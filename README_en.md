# PaddlePDF

A PDF text recognition tool based on PaddleOCR, supporting both **CLI** and **GUI** modes.

> **[中文版](README.md)** | English

## Features

- **GPU/CPU Dual Mode**: Auto-detects NVIDIA GPU with CUDA acceleration
- **7 Language Models**: Chinese, English, Japanese, Korean, Russian, etc., powered by PP-OCRv4
- **Searchable PDF**: Precise glyph width measurement + baseline vertical centering; transparent text layer (Render Mode 3) aligned with background text
- **Plain Text Output**: Saves OCR results as text files (with optional confidence scores)
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

Requires the [pixi](https://pixi.sh) package manager.

```bash
# Basic install (CLI)
pixi install

# Install GUI dependencies (includes pytauri)
pixi install --environment gui
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

```bash
# Development mode (hot reload)
pixi run tauri-dev

# Production build
pixi run tauri-build
```

### GUI Features

- 📄 **Drag & Drop**: Drag in PDF files, supports batch processing
- 🔄 **Real-Time Progress**: Page-by-page OCR processing progress
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
│   │   ├── model_service.py  #     Model management
│   │   └── system_service.py #     System diagnostics
│   ├── controller/           #   Controller layer (protocol adapters)
│   │   ├── cli_controller.py #     argparse CLI
│   │   └── ipc_controller.py #     pytauri IPC endpoints
│   ├── common/               #   Shared definitions
│   │   ├── schemas.py        #     Data structures
│   │   ├── events.py         #     Event constants
│   │   └── config.py         #     Global config
│   └── app/                  #   App entry points
│       ├── cli_app.py        #     CLI entry
│       └── pytauri_app.py    #     GUI entry
├── src-frontend/             # Vue 3 frontend
│   ├── src/
│   │   ├── views/            #     Page components
│   │   ├── components/       #     Reusable components
│   │   ├── stores/           #     Pinia state management
│   │   ├── composables/      #     Composable functions
│   │   └── types/            #     TypeScript types
│   └── src-tauri/            #     Tauri Rust shell
├── doc/                      # Documentation
├── pixi.toml                 # Python dependencies config
└── README.md
```

## Tech Stack

| Layer | Technology |
|---|---|
| Desktop Shell | [Tauri 2.x](https://tauri.app) (Rust) |
| Python Bridge | [pytauri](https://github.com/pytauri/pytauri) |
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
