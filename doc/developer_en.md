# Developer Guide

## Project Overview

A PDF text recognition tool based on PaddleOCR, supporting both **CLI** and **GUI** modes. The GUI uses FastAPI + Uvicorn as a Python backend sidecar, with the frontend rendered by Tauri + Vue 3, communicating loosely coupled via HTTP and Server-Sent Events (SSE) streams.

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Desktop Shell | Tauri | 2.11 |
| Communication | FastAPI + Uvicorn (HTTP / SSE) | 0.115+ / 0.34+ |
| Frontend Framework | Vue 3 + TypeScript | 3.5 |
| UI Components | Naive UI | 2.44 |
| Build Tools | Vite | 8.0 |
| CSS | UnoCSS | 66.7 |
| State Management | Pinia | 3.0 |
| OCR Engine | PaddleOCR | 3.4.1 |
| PDF Processing | PyMuPDF (fitz) | 1.25+ |
| Python | CPython | 3.12 |
| GPU | PaddlePaddle GPU | 3.3.0 (CUDA 12.6) |
| Package Manager | pixi + pnpm | — |

## Project Structure (MVC Architecture)

```
paddle_pdf/
├── src/paddle_pdf/           # Python backend
│   ├── core/                 #   Model — pure business logic, no UI dependency
│   │   ├── ocr_engine.py     #     PaddleOCR engine wrapper
│   │   ├── pdf_pipeline.py   #     PDF processing pipeline
│   │   ├── models.py         #     Model registry (7 languages)
│   │   └── gpu_utils.py      #     CUDA detection
│   ├── service/              #   Service — orchestrates core, reports progress via callbacks
│   │   ├── ocr_service.py    #     OCR task orchestration
│   │   ├── task_queue.py     #     Background task queue (ThreadPoolExecutor)
│   │   ├── model_service.py  #     Model management
│   │   └── system_service.py #     System diagnostics
│   ├── controller/           #   Controller — protocol adapter layer
│   │   └── cli_controller.py #     argparse CLI parameter parsing
│   ├── common/               #   Shared definitions
│   │   ├── schemas.py        #     dataclass data structures
│   │   ├── events.py         #     Communication event constants
│   │   └── config.py         #     Global config
│   └── app/                  #   App entry points
│       ├── cli_app.py        #     CLI entry
│       └── http_server.py    #     FastAPI Web server entry (Sidecar)
│
├── src-frontend/             # Vue 3 frontend
│   ├── src/
│   │   ├── views/            #     HomeView, TaskDetailView, SettingsView
│   │   ├── components/       #     FileDropZone, TaskCard, TaskProgress,
│   │   │                     #     ModelSelector, GpuStatus, TextPanel
│   │   ├── stores/           #     Pinia: task, settings, app
│   │   ├── composables/      #     useIpc (HTTP/SSE wrappers), useTask, useModels
│   │   └── types/            #     TypeScript type definitions
│   └── src-tauri/            #     Tauri Rust shell
│       ├── src/main.rs       #       Main entry (spawns Sidecar, reads free port)
│       └── tauri.conf.json   #       Tauri configuration (resource copying and packaging)
│
├── doc/                      # Documentation
├── pixi.toml                 # Python + Node dependency management
└── README.md
```

## FastAPI Sidecar Architecture & Communication

### Communication Flow

```
┌─────────────────┐       HTTP Request (GET / POST)      ┌──────────────────┐
│  Vue Frontend   │ ───────────────────────────────────→ │  FastAPI Backend │
│  (useIpc.ts)    │                                      │  (Uvicorn)       │
│                 │ ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  └──────────────────┘
└─────────────────┘      Server-Sent Events (SSE)                 │
                                                                  │
                                                           Routes & Tasks
                                                                  ↓
                                                         ┌──────────────┐
                                                         │  Service Lyr │
                                                         │  Core Layer  │
                                                         └──────────────┘
```

### Key Implementation Details

1. **Process Spawning & Lifecycle Management** (`src-frontend/src-tauri/src/main.rs`):
   - The Tauri main process spawns the Python backend process during its initialization (`setup` hook).
   - In development mode, it checks for a compiled dev backend executable (`backend/dist/paddle_pdf_backend/paddle_pdf_backend.exe`). If not found, it runs the pixi environment Python (`python.exe` executing `-m paddle_pdf.app.http_server`) with `PYTHONPATH` pointing to the workspace root.
   - In production packaging, Tauri resolves the sidecar from its bundled resource directory and launches `paddle_pdf_backend.exe`.
2. **Dynamic Port Handshake & Service Discovery**:
   - The Python backend binds to a random free port on local loopback `127.0.0.1` (obtained via `socket.bind(("", 0))`) and outputs `PADDLE_PDF_PORT=<port>` to standard output (stdout) at startup.
   - The Rust Tauri process intercepts the sidecar process's stdout, parses this line via a `BufReader`, and stores the port in Tauri's application state (`BackendState`).
   - The frontend calls the Tauri command `get_backend_port` to obtain the port, then communicates via standard HTTP and SSE.
3. **Orphan Process Auto-Cleanup (PID Watcher)**:
   - To prevent the Python backend process from remaining in memory if the Tauri frontend crashes or is force-killed, Rust passes the Tauri process ID via the `PADDLE_PDF_PARENT_PID=<parent_pid>` environment variable.
   - The Python backend (`http_server.py`) spawns a background watcher daemon thread that periodically checks the health of the parent PID (on Windows using `OpenProcess` with `GetExitCodeProcess` looking for `STILL_ACTIVE`; on Unix via `os.kill(pid, 0)`). If the parent process is dead, the sidecar invokes `os._exit(0)` to self-terminate.

### HTTP Routes & SSE Event Bus

1. **API Invocation** (`useIpc.ts`):
   - The frontend maps commands to HTTP endpoints (e.g., `process_task` maps to `POST /process_task`) and calls them via standard HTTP GET or POST requests using `fetch`.
2. **Push Event Streams**:
   - The backend exposes a `/events` endpoint that supports Server-Sent Events (SSE). The frontend establishes a persistent connection using HTML5 `EventSource` to subscribe to updates.
   - Task execution status (progress, completion, failures, model downloads) is pushed to all connected SSE clients via an asynchronous event queue.

---

## Task Queue Architecture (TaskQueue)

### Design Overview

`TaskQueue` (`src/paddle_pdf/service/task_queue.py`) implements a background task queue for sequential OCR task execution:

- **Async submission**: `add_task()` returns immediately; the task runs in a background thread
- **Sequential processing**: `max_workers=1` (default), as GPU memory rarely allows concurrent models
- **Task isolation**: Each task gets its own `OcrService` instance — model state never leaks between tasks
- **Callback mechanism**: 4 callback types (progress/completion/failure/cancel) trigger SSE events to the frontend

### Core Classes

```
TaskQueue
├── _tasks: dict[str, QueuedTask]    # All tasks (indexed by task_id)
├── _queue: list[str]                # task_ids waiting to run (FIFO)
├── _active: dict[str, OcrService]   # Currently running tasks
├── _executor: ThreadPoolExecutor    # Background thread pool
└── _lock: threading.Lock            # Thread-safety lock
```

### Sidecar Communication Event Flow

```
Backend TaskQueue                    FastAPI /events (SSE)              Frontend (useTask.ts)
─────────────────                    ─────────────────────              ──────────────────────
progress_callback(task_id, tp)  ──→  SSE [task://progress]        ──→   store.updateProgress
completion_callback(task_id, r) ──→  SSE [task://completed]       ──→   store.completeTask
failure_callback(task_id, err)  ──→  SSE [task://failed]          ──→   store.failTask
cancel_callback(task_id)        ──→  SSE [task://cancelled]       ──→   store.cancelTask
```

### Sidecar HTTP API Routes

| Endpoint | Method | Description | Returns |
|---|---|---|---|
| `/process_task` | `POST` | Submit task to queue (returns immediately) | `SimpleResponse` |
| `/cancel_task` | `POST` | Cancel a specific task | `SimpleResponse` |
| `/queue_status` | `GET` | Get snapshot of all task statuses | `list[TaskStatus]` |
| `/remove_task` | `POST` | Remove a completed/failed/cancelled task | `SimpleResponse` |
| `/list_models` | `GET` | Get list of available OCR models | `list[ModelInfo]` |
| `/download_model`| `POST` | Trigger model download in background | `SimpleResponse` |
| `/check_gpu` | `GET` | Check system GPU/CUDA status | `GpuInfo` |

### Frontend Task Store

Pinia `task` store maintains the task list with computed slices:

- `pendingTasks`: status === 'pending'
- `activeTasks`: status ∈ ['extracting', 'ocr_running', 'saving']
- `completedTasks`: status === 'completed'
- `finishedTasks`: status ∈ ['completed', 'failed', 'cancelled']

### Frontend Event Listeners

The `useTask` composable registers global event listeners via `ipcListen` on first call, routing events by `task_id`:

```typescript
ipcListen<TaskProgress>('task://progress', (progress) => {
  store.updateProgress(progress.task_id, progress)
})
ipcListen<TaskCompletedEvent>('task://completed', (payload) => {
  store.completeTask(payload.task_id, payload)
})
```
```

## PaddleOCR 3.x API Key Differences

### Constructor Parameters

| Old Parameter (2.x) | New Parameter (3.x) | Notes |
|---|---|---|
| `use_gpu=True/False` | **Removed** | Use `paddle.device.set_device("gpu:0")` instead |
| `show_log=False` | **Removed** | No longer supported |
| `use_angle_cls=True` | `use_textline_orientation=True` | Parameter renamed |

### Return Result Format

```python
# Old 2.x: [[bbox, (text, score)], ...]
# New 3.x: [OCRResult] (dict-like)

ocr_result = raw_result[0]
rec_texts = ocr_result["rec_texts"]     # list[str]
rec_scores = ocr_result["rec_scores"]   # list[float] (0-1)
rec_polys = ocr_result["rec_polys"]     # list[polygon], each polygon = [[x,y]×4]
```

### Bbox Processing

```python
import numpy as np

pts = np.array(bbox)         # shape (4, 2)
x0, y0 = pts.min(axis=0)
x1, y1 = pts.max(axis=0)
```

## PDF Searchable Layer Writing

Uses PyMuPDF (fitz) to overlay OCR text onto the original PDF in fully transparent mode (`render_mode=3`).

### Core Algorithm

1. **High-Resolution Detection Limit**: To address small font (like headers, superscripts) disappearing or merging, a custom detection limit is used. Under GPU execution, `text_det_limit_side_len` defaults to `4320` (supporting lossless detection for A4/B5 pages up to 500 DPI); under CPU, it defaults to `1920` to balance quality with memory and processing time.
2. **Font Pre-registration & Embedding**: Detects system CJK fonts, falls back to PyMuPDF's built-in `cjk` font package.
3. **Font Size Matching (Width-first, Height-truncated Tolerance)**: Prioritizes width-matching (`fs_by_width`), only truncating at a strict height-limit if it exceeds 1.05 times the target height, ensuring the text highlight selection bounding box aligns perfectly with the underlying images.
4. **Adaptive Character Spacing (TextWriter Single Character Appends)**: Uses `fitz.TextWriter` to append character-by-character, dynamically computing and distributing spacing gap as `(target_width - text_width) / (n - 1)` to keep visual spaces and spacing in multi-word/character structures.
5. **Precise Baseline Placement & Constraint**: Vertically centers the text within the detected bounding box, aligning it using ascenders: `baseline_y = ry0 + (target_height - fontsize) / 2 + ascender * fontsize`. This guarantees that when the OCR bounding box includes extra whitespace or line-separators, the overlay text remains strictly bound and centered inside the `[ry0, ry1]` boundaries, eliminating vertical drift in headers, abstracts, and titles.

## Environment Setup

```bash
# Install all dependencies (including Node.js, pnpm)
pixi install

# CLI
pixi run run -- -i "book.pdf"

# GUI development mode
pixi run tauri-dev

# GUI production build
pixi run tauri-build

# GPU diagnostics
pixi run check-gpu
```

## Common Error Quick Reference

| Error | Cause | Fix |
|---|---|---|
| `Unknown argument: use_gpu` | PaddleOCR 3.x removed this parameter | Use `paddle.device.set_device()` instead |
| `Unknown argument: use_angle_cls` | Parameter renamed | Use `use_textline_orientation=True` |
| `not enough values to unpack bbox` | Bbox is a 4-point polygon | Use `np.array(bbox)` to extract min/max |
| `partially initialized module 'paddle' has no attribute 'tensor' (circular import)` | Initialization order issues in the packaged environment leading to circular imports | Explicitly import base submodules (`paddle.base`, `paddle.tensor`, `paddle.nn`, `paddle.device`) at the very beginning of the PyInstaller runtime hook `rth_paddle.py` |
| `No module named 'unittest'` (or `importlib.metadata.PackageNotFoundError`) | The packaged binary environment lacks standard `.dist-info` metadata folders, causing dependency version checks to crash | Monkeypatch `importlib.metadata.version` in `rth_paddle.py` to intercept searches and return mock version strings (e.g., `4.10.0.84` for opencv) if the module is actually importable |
| GPU check returns False / CUDA DLLs not found in packaged build | Massive NVIDIA CUDA/cuDNN DLLs are not bundled to reduce binary size; system fails to locate local CUDA installations | Ensure local CUDA Toolkit 12.x and cuDNN are installed, and their `bin/` directories are in the PATH. The packaged app's runtime hook `rth_paddle.py` automatically scans standard paths and registers them using `os.add_dll_directory` |
| `No module named 'paddle_pdf'` | PYTHONPATH not set | Set `PYTHONPATH = "../src"` in pixi.toml tauri tasks or use the correct python run commands |

## Known Limitations

- **Layout Reading Order**: Complex multi-column layouts may not follow the correct reading order in plain text export
- **Very Small or Very Large Characters**: Font size scaling has a lower limit of 1.0pt
- **System Font Dependency**: Auto-searches for common Chinese fonts, falls back to built-in `cjk` font package
- **Model Cache**: `~/.paddleocr/` and `~/.paddlex/`
