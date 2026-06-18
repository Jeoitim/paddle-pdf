# Developer Guide

## Project Overview

A PDF text recognition tool based on PaddleOCR, supporting both **CLI** and **GUI** modes. The GUI is built with pytauri (Python + Tauri + Vue 3) for cross-platform desktop applications.

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Desktop Shell | Tauri | 2.11 |
| Python Bridge | pytauri | 0.4 |
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
│   │   ├── cli_controller.py #     argparse CLI
│   │   └── ipc_controller.py #     pytauri IPC endpoints (14 commands)
│   ├── common/               #   Shared definitions
│   │   ├── schemas.py        #     dataclass data structures
│   │   ├── events.py         #     IPC event constants
│   │   └── config.py         #     Global config
│   └── app/                  #   App entry points
│       ├── cli_app.py        #     CLI entry
│       └── pytauri_app.py    #     GUI entry (pytauri)
│
├── src-frontend/             # Vue 3 frontend
│   ├── src/
│   │   ├── views/            #     HomeView, TaskDetailView, SettingsView
│   │   ├── components/       #     FileDropZone, TaskCard, TaskProgress,
│   │   │                     #     ModelSelector, GpuStatus, TextPanel
│   │   ├── stores/           #     Pinia: task, settings, app
│   │   ├── composables/      #     useIpc, useTask, useModels
│   │   └── types/            #     TypeScript type definitions
│   └── src-tauri/            #     Tauri Rust shell
│       ├── src/lib.rs        #       pytauri extension module (pymodule_export)
│       ├── src/main.rs       #       Python embedding entry (PythonInterpreterBuilder)
│       └── tauri.conf.json   #       Tauri config
│
├── doc/                      # Documentation
├── pixi.toml                 # Python + Node dependencies
└── README.md
```

## pytauri Architecture Deep Dive

### IPC Communication Flow

```
┌─────────────────┐     pyInvoke("cmd", body)     ┌──────────────────┐
│  Vue Frontend   │ ─────────────────────────────→ │  Tauri Plugin    │
│  (useIpc.ts)    │                                │  (pyfunc handler)│
│                 │ ← ─ ─ Emitter.emit(event) ─ ─ ─│                  │
└─────────────────┘                                └──────────────────┘
                                                          │
                                                    invoke_handler
                                                          ↓
                                                   ┌──────────────┐
                                                   │  pytauri      │
                                                   │  Commands     │
                                                   │  (Python)     │
                                                   └──────────────┘
                                                          │
                                                          ↓
                                                   ┌──────────────┐
                                                   │  Service Layer│
                                                   │  Core Layer   │
                                                   └──────────────┘
```

### Key Implementation Details

1. **Rust `lib.rs`**: Creates a Python extension module via `pytauri::pymodule_export`, exporting `context_factory` and `builder_factory`
2. **Rust `main.rs`**: Uses `PythonInterpreterBuilder` (standalone mode) to embed a Python interpreter and run the entry module
3. **Python `pytauri_app.py`**: Registers IPC commands via `Commands`, processes asynchronously through `BlockingPortal`
4. **Frontend `useIpc.ts`**: Uses `pyInvoke` (from `tauri-plugin-pytauri-api`) instead of native `invoke`
5. **pytauri command signature**: `async def cmd(body: BaseModel) -> BaseModel | bytes`, where `body` and `app_handle` are special parameter names

### Command Registration Conventions

```python
from pytauri import Commands, AppHandle, Emitter
from pydantic import BaseModel

commands = Commands()

class MyRequest(BaseModel):
    name: str

class MyResponse(BaseModel):
    message: str

@commands.command()
async def my_command(body: MyRequest) -> MyResponse:
    return MyResponse(message=f"Hello {body.name}")

# Commands with no arguments use EmptyBody
class EmptyBody(BaseModel): pass

@commands.command()
async def no_args(body: EmptyBody) -> bytes:
    return b"ok"

# Commands that emit events add an app_handle parameter
@commands.command()
async def with_progress(body: MyRequest, app_handle: AppHandle) -> MyResponse:
    Emitter.emit(app_handle, "progress", ProgressPayload(...))
    return MyResponse(message="done")
```

### Important Notes

- **Do NOT use `from __future__ import annotations`**: pytauri's `wrap_pyfunc` needs runtime type annotations for `issubclass` checks
- **`app_handle` parameter type must be `AppHandle`**: Cannot use `Any`
- **Commands returning `bytes`**: The frontend receives raw bytes and must manually `JSON.parse`
- **`PYTHONPATH` must include the `src/` directory**: Set via env in pixi.toml's tauri tasks

## Task Queue Architecture (TaskQueue)

### Design Overview

`TaskQueue` (`src/paddle_pdf/service/task_queue.py`) implements a background task queue for sequential OCR task execution:

- **Async submission**: `add_task()` returns immediately; the task runs in a background thread
- **Sequential processing**: `max_workers=1` (default), as GPU memory rarely allows concurrent models
- **Task isolation**: Each task gets its own `OcrService` instance — model state never leaks between tasks
- **Callback mechanism**: 4 callback types (progress/completion/failure/cancel) route events to the frontend

### Core Classes

```
TaskQueue
├── _tasks: dict[str, QueuedTask]    # All tasks (indexed by task_id)
├── _queue: list[str]                # task_ids waiting to run (FIFO)
├── _active: dict[str, OcrService]   # Currently running tasks
├── _executor: ThreadPoolExecutor    # Background thread pool
└── _lock: threading.Lock            # Thread-safety lock
```

### IPC Event Flow

```
Backend TaskQueue                    Frontend (useTask.ts)
─────────────────                    ──────────────────────
progress_callback(task_id, tp)  ──→  task://progress → store.updateProgress
completion_callback(task_id, r) ──→  task://completed → store.completeTask
failure_callback(task_id, err)  ──→  task://failed → store.failTask
cancel_callback(task_id)        ──→  task://cancelled → store.cancelTask
```

### IPC Command Summary

| Command | Description | Returns |
|---|---|---|
| `process_task` | Submit task to queue (returns immediately) | `SimpleResponse` |
| `cancel_task` | Cancel a specific task | `SimpleResponse` |
| `get_queue_status` | Get snapshot of all task statuses | `bytes` (JSON) |
| `remove_task` | Remove a completed/failed/cancelled task | `SimpleResponse` |

### Frontend Task Store

Pinia `task` store maintains the task list with computed slices:

- `pendingTasks`: status === 'pending'
- `activeTasks`: status ∈ ['extracting', 'ocr_running', 'saving']
- `completedTasks`: status === 'completed'
- `finishedTasks`: status ∈ ['completed', 'failed', 'cancelled']

### Frontend Event Listeners

The `useTask` composable registers global event listeners on first call (`ensureListeners()`), routing events by `task_id`:

```typescript
ipcListen<TaskProgress>('task://progress', (progress) => {
  store.updateProgress(progress.task_id, progress)
})
ipcListen<TaskCompletedEvent>('task://completed', (payload) => {
  store.completeTask(payload.task_id, result)
})
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
| `issubclass() arg 1 must be a class` | Used `from __future__ import annotations` | Remove the import, use Python 3.12 native annotations |
| `Command X not found` | Frontend used `invoke` instead of `pyInvoke` | Use `pyInvoke` from `tauri-plugin-pytauri-api` |
| `pytauri.pyfunc not allowed` | Tauri permissions not configured | Add `pytauri:default` to capabilities |
| `No module named 'paddle_pdf'` | PYTHONPATH not set | Set `PYTHONPATH = "../src"` in pixi.toml tauri tasks |
| PyO3 doesn't support Python 3.14 | System Python version too new | Use pixi's Python 3.12, set `PYO3_PYTHON` |

## Known Limitations

- **Layout Reading Order**: Complex multi-column layouts may not follow the correct reading order in plain text export
- **Very Small or Very Large Characters**: Font size scaling has a lower limit of 1.0pt
- **System Font Dependency**: Auto-searches for common Chinese fonts, falls back to built-in `cjk` font package
- **Model Cache**: `~/.paddleocr/` and `~/.paddlex/`
