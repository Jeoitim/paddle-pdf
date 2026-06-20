# PaddlePDF

<div align="center">
<img src="doc/paddlepdf-icon.png" alt="PaddlePDF Banner" width="50%" />
</div>

<div align="center">
<strong>A high-precision, low-barrier, GPU-accelerated local OCR extraction and transparent text layer synthesis tool.</strong>
</div>

**[中文版](README.md)** | English

---

A PDF text recognition tool based on PaddleOCR, supporting both **CLI** and **GUI** modes.

## Features

- **GPU/CPU Dual Mode**: Auto-detects NVIDIA GPU with CUDA acceleration
- **7 Language Models**: Chinese, English, Japanese, Korean, Russian, etc., powered by PP-OCRv4
- **Searchable PDF**: Precise glyph width measurement + baseline vertical centering; transparent text layer (Render Mode 3) aligned with background text
- **Plain Text Output**: Saves OCR results as text files (with optional confidence scores)
- **Task Queue**: Background sequential execution of multiple OCR tasks with queuing, cancellation, and per-task model isolation
- **GUI**: Drag-and-drop files, real-time progress, model management, GPU status detection

> **⚠️ Note on Searchable PDF Quality**
>
> The positioning accuracy of the searchable text layer depends heavily on:
> - **Layout complexity**: Simpler layouts (single column, no mixed text/images) produce better results
> - **Source file clarity**: Higher quality scans/photos lead to more accurate OCR and tighter text alignment
> - **Model size**: Larger models (e.g., `ch_server_v2`) significantly outperform lightweight ones
>
> If the source file quality is mediocre, a smaller model is used, or CUDA acceleration is unavailable, the experience degrades significantly. **Do not expect out-of-the-box accuracy** — choose the appropriate model and DPI settings based on your needs.

## 💾 Installation Guide

To accommodate different needs, we provide both **One-Click Installation for General Users** and **Local Development Setup for Developers**.

### 1. For General Users (Recommended)

General users **do not** need to install Python, Node.js, Pixi, or Git. Simply download and install the packaged application:

1. Go to the [Releases page](https://github.com/Jeoitim/paddle_pdf/releases) and download the latest installer (e.g., `PaddlePDF_1.0.0_x64-setup.exe`).
2. Run the installer and follow the prompt wizard to complete setup.
3. Once installed, double-click the **PaddlePDF** shortcut on your desktop to run the application.

> 💡 **GPU Acceleration Note**: If you want to use your NVIDIA GPU for accelerated text recognition, please refer to the [GPU Requirements](#gpu-requirements) section below for simple CUDA & cuDNN configurations.

---

### 2. For Developers (Local Source & Debugging)

If you wish to debug, run from source, or contribute to code, configure your environment as follows:

- **Prerequisites**: Install the [Pixi](https://pixi.sh) package manager and the [pnpm](https://pnpm.io) package manager.
- **Environment Setup**:
  ```bash
  # 1. Install Python core and basic dependencies (automatically managed by pixi in an isolated environment)
  pixi install

  # 2. Install frontend Node.js dependencies
  pixi run frontend-install
  ```

---

## 🚀 User Guide

### 1. General User Operations

#### ▌ Mode A: Graphical User Interface (GUI) Mode
Double-click the desktop shortcut to start **PaddlePDF**.
- Drag and drop PDF files into the application for batch processing in a task queue.
- Manage/download 7 language OCR models and monitor system GPU status.

#### ▌ Mode B: Command-Line Interface (CLI) Mode (Standalone Executable)
Once installed, the backend engine `paddle_pdf_backend.exe` runs completely independent of local Python environments. You can invoke it directly from CMD/PowerShell as a standalone CLI tool.
- **Default Executable Path**:
  `C:\Users\<Your Windows Username>\AppData\Local\PaddlePDF\resources\paddle_pdf_backend\paddle_pdf_backend.exe`
- **Usage Examples**:
  ```bash
  # 1. Navigate to the backend engine folder
  cd "C:\Users\<Your Windows Username>\AppData\Local\PaddlePDF\resources\paddle_pdf_backend"

  # 2. Check local GPU / CUDA environment
  paddle_pdf_backend.exe --diagnose

  # 3. List all available OCR models
  paddle_pdf_backend.exe --list-models

  # 4. Perform text recognition on a PDF (CPU mode, outputs are generated in the input PDF's folder)
  paddle_pdf_backend.exe -i "D:\path\to\book.pdf"

  # 5. Perform OCR using GPU acceleration and a specific model
  paddle_pdf_backend.exe -gpu -model ch_plus -i "D:\path\to\book.pdf"
  ```
- **Command-Line Arguments**:

| Argument | Description | Default |
|---|---|---|
| `-i, --input` | **Required**, input PDF file path (absolute or relative) | — |
| `-gpu` | Enable GPU acceleration (requires CUDA setup) | Off |
| `-model <name>` | OCR model name (ch/ch_plus/ch_server_v2/en/...) | ch |
| `-o <dir>` | Output directory | `<filename>_ocr_output/` |
| `--max-pages N` | Maximum pages to process | All |
| `--dpi N` | Render resolution (400 recommended for dense text) | 300 |
| `--conf` | Include confidence scores in output text file (.txt) | Off |
| `--list-models` | List all available models and exit | — |
| `--diagnose` | Diagnose local CUDA and GPU status and exit | — |
| `-v` | Verbose output | Off |

- **Output Files**: Upon completion, the tool generates `<filename>_searchable.pdf` (fully copyable and Ctrl+F searchable PDF with transparent text layer) and `<filename>_text.txt` (recognized raw text output).

---

### 2. Developer Operations & Debugging

#### ▌ Local Development Hot Reload
For local development, start the frontend (Vite) and backend (FastAPI) separately in two terminal windows:

```bash
# Terminal 1: Start the Python FastAPI backend sidecar service
pixi run backend-dev

# Terminal 2: Start the frontend GUI webview
pixi run tauri-dev
```

#### ▌ Local CLI Execution
Directly execute CLI commands using Pixi tasks under the development env:
```bash
# CPU mode
pixi run run -- -i "book.pdf"

# GPU mode
pixi run run-gpu -- -i "book.pdf"
```

#### ▌ Production Packaging
When your changes are ready, compile and bundle the application:
```bash
# 1. Compile Python backend to a standalone executable folder (dist/paddle_pdf_backend/)
pixi run build-backend

# 2. Invoke Rust tauri build to compile the webview assets and generate the final NSIS installer
pixi run tauri-build
```

## GUI Features

- 📄 **Drag & Drop**: Drag in PDF files, supports batch queue processing
- 🔄 **Real-Time Progress**: Page-by-page OCR processing progress, cancel running/queued tasks
- 🧠 **Model Management**: View/download/switch between 7 OCR models
- 💻 **GPU Status**: Auto-detects CUDA environment, shows GPU availability
- 🌙 **Dark Mode**: Light/dark theme toggle, settings auto-saved
- 📊 **Results Display**: Page count, line count, confidence, elapsed time
- 📂 **Quick Actions**: One-click to open output file/folder

## GPU Requirements

| Component | Description |
|---|---|
| NVIDIA GPU | RTX 3060+ (6GB+) recommended |
| CUDA Toolkit | 11.x or 12.x |
| cuDNN | Must be installed separately |

```bash
pixi run check-gpu  # Verify GPU environment
```

## Project Structure

```
paddle_pdf/
├── src/paddle_pdf/           # Python backend (MVC architecture)
│   ├── core/                 #   Core business logic (no UI dependency)
│   │   ├── ocr_engine.py     #     PaddleOCR engine wrapper
│   │   ├── pdf_pipeline.py   #     PDF processing pipeline
│   │   ├── models.py         #     Model registry
│   │   └── gpu_utils.py      #     CUDA detection
│   ├── service/              #   Service layer (orchestrates core logic)
│   │   ├── ocr_service.py    #     OCR task orchestration
│   │   ├── task_queue.py     #     Background task queue
│   │   ├── model_service.py  #     Model management
│   │   └── system_service.py #     System diagnostics
│   ├── controller/           #   Controller layer (protocol adapters)
│   │   └── cli_controller.py #     argparse CLI parameter parsing
│   ├── common/               #   Shared definitions
│   │   ├── schemas.py        #     Data structures
│   │   ├── events.py         #     Communication event constants
│   │   └── config.py         #     Global config
│   └── app/                  #   App entry points
│       ├── cli_app.py        #     CLI entry
│       └── http_server.py    #     FastAPI Web server entry (Sidecar)
├── src-frontend/             # Vue 3 frontend
│   ├── src/
│   │   ├── views/            #     Page views
│   │   ├── stores/           #     Pinia state management
│   │   └── composables/      #     useIpc.ts (via HTTP and SSE events)
│   └── src-tauri/            #     Tauri Rust shell
│       ├── src/main.rs       #       Main entry (spawns backend sidecar and parses dynamic port)
│       └── tauri.conf.json   #       Tauri configuration (sets bundled resource copies)
├── doc/                      # Documentation
├── pixi.toml                 # Pixi Python + Node environment configuration
└── README.md
```

## Tech Stack

| Layer | Technology |
|---|---|
| Desktop Shell | [Tauri 2.x](https://tauri.app) (Rust) |
| Communication | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn (HTTP / SSE subscription) |
| Frontend Framework | [Vue 3](https://vuejs.org) + TypeScript |
| UI Components | [Naive UI](https://www.naiveui.com) |
| Build Tools | [Vite](https://vitejs.dev) + [pnpm](https://pnpm.io) |
| CSS | [UnoCSS](https://unocss.dev) |
| State Management | [Pinia](https://pinia.vuejs.org) |
| OCR Engine | [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) 3.4.1 |
| PDF Processing | [PyMuPDF](https://github.com/pymupdf/PyMuPDF) |
| Package Manager | [pixi](https://pixi.sh) (Python) + pnpm (Node) |

## Documentation

- [User Guide](doc/user-guide_en.md) — Detailed usage, examples, troubleshooting
- [Developer Guide](doc/developer_en.md) — Project architecture, API differences, gotchas

## License

MIT License
