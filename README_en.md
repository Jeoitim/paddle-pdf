# PaddlePDF

A PDF text recognition tool based on PaddleOCR, supporting both **CLI** and **GUI** modes.

> **[中文版](README.md)** | English

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

## Installation

Requires the [pixi](https://pixi.sh) package manager and [pnpm](https://pnpm.io).

```bash
# 1. Install Python backend and basic dependencies (automatically managed by pixi)
pixi install

# 2. Install frontend Node.js dependencies
pixi run frontend-install
```

## CLI Usage

```bash
# CPU mode
pixi run run -- -i "book.pdf"

# GPU mode
pixi run run-gpu -- -i "book.pdf"

# High-accuracy model + GPU
pixi run run-gpu -- -gpu -model=ch_plus -i "book.pdf"

# Process only the first 5 pages
pixi run run -- -i "book.pdf" --max-pages 5

# List all models
pixi run run -- --list-models
```

### Command-Line Arguments

| Argument | Description | Default |
|---|---|---|
| `-i, --input` | **Required**, input PDF file | — |
| `-gpu` | Enable GPU acceleration | Off |
| `-model <name>` | OCR model (ch/ch_plus/ch_server_v2/en/...) | ch |
| `-o <dir>` | Output directory | `<filename>_ocr_output/` |
| `--max-pages N` | Max pages to process | All |
| `--dpi N` | Render resolution | 300 |
| `--conf` | Include confidence in text output | Off |
| `--list-models` | List all available models | — |
| `-v` | Verbose output | Off |

### Output

| File | Description |
|---|---|
| `<filename>_searchable.pdf` | PDF with text layer, searchable/copyable |
| `<filename>_text.txt` | Plain text, confidence scores off by default |

## GUI Usage

### Development Mode (Hot Reload)

In the development environment, the frontend and backend services must be started in two separate terminal windows:

```bash
# Terminal 1: Start the Python FastAPI backend service
pixi run backend-dev

# Terminal 2: Start the frontend GUI
pixi run tauri-dev
```

### Production Packaging

```bash
# 1. Compile the Python backend into a standalone executable
pixi run build-backend

# 2. Invoke Rust tauri build to construct the NSIS installer
pixi run tauri-build
```

### GUI Features

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
