# User Guide

## ⚠️ Important: Searchable PDF Quality Expectations

The positioning accuracy of the searchable text layer depends heavily on:

- **Layout complexity**: Simpler layouts (single column, no mixed text/images) produce better results
- **Source file clarity**: Higher quality scans/photos lead to more accurate OCR and tighter text alignment
- **Model size**: Larger models (e.g., `ch_plus` or `ch_server_v2`) significantly outperform lightweight ones

If the source file quality is mediocre, a smaller model is used, or CUDA acceleration is unavailable, the experience degrades significantly. **Do not expect out-of-the-box 100% accuracy** — choose the appropriate model and DPI settings based on your needs.

---

## Quick Start

We provide two separate installation and usage routes for different types of users:

### Installation Guide

#### 1. For General Users (Recommended, One-Click Installation)
General users **do not** need to install Git, Python, Node.js, Pixi, or C++ compiler environments:
1. Go to the [Releases page](https://github.com/Jeoitim/paddle_pdf/releases) and download the latest pre-packaged installer (e.g., `PaddlePDF_1.0.0_x64-setup.exe`).
2. Double-click the installer and follow the instructions to complete setup. Once installed, you can launch the graphical user interface (GUI) from your desktop shortcut.

#### 2. For Developers & Advanced Users (Local Source & Development)
If you wish to run from source and debug locally, configure your environment as follows:
- Ensure the [Pixi](https://pixi.sh) package manager and the [pnpm](https://pnpm.io) package manager are installed.
- Run the following commands in the project root directory:
  ```bash
  # Automatically pull Python runtime and OCR packages
  pixi install

  # Install frontend Vue and Tauri Node.js dependencies
  pixi run frontend-install
  ```

---

## Graphical User Interface (GUI) Mode Usage

The GUI (Graphical User Interface) is the preferred mode for most general users, providing intuitive controls and real-time status feedback.

### Core Features

- 📄 **Drag & Drop**: Drag in one or multiple PDF files to process them sequentially in a background task queue.
- 🔄 **Real-Time Progress**: Displays page-by-page progress; support for cancelling active or pending tasks.
- 🧠 **Model Management**: View, download, and switch between 7 different OCR models.
- 💻 **GPU Status**: Automatically detects CUDA environments and displays current GPU availability.
- 🌙 **Dark Mode**: Toggle light and dark themes; preferences are auto-saved.
- 📂 **Quick Actions**: Double-click a task card or click action buttons to open output files or their containing folders.

### Task Queue & Statuses

The GUI features a background queue manager (executes sequentially with `max_workers=1` to prevent GPU memory overflow):
- `pending`: Waiting in queue.
- `extracting` / `ocr_running` / `saving`: Currently processing (extracting pages, running OCR, or generating the final PDF).
- `completed`: Successfully completed. Click to open directly.
- `failed`: Processing failed (hover or click to view the error log).
- `cancelled`: Manually cancelled by the user.

---

## Command-Line Interface (CLI) Mode Usage (For Advanced Users & Developers)

The backend engine supports a wide range of CLI arguments, making it easy to run batch operations or integrate with automation scripts.

### 1. Running Commands (Development vs Production)

The startup command depends on your environment:

#### ▌ Route A: Local Development Environment (Running from Source)
In a development environment, you must prefix commands with the **Pixi** package manager to run within the isolated environment.
*   **Format**: You must include a double dash `--` to pass arguments to the underlying python script!
*   **CPU Mode**:
    ```bash
    pixi run run -- -i "path/to/book.pdf"
    ```
*   **GPU Mode**:
    ```bash
    pixi run run-gpu -- -i "path/to/book.pdf"
    ```

#### ▌ Route B: Production Packaged Version
Once compiled or installed, the backend engine `paddle_pdf_backend.exe` is completely independent of local Python environments. You can run it directly as a standalone CLI tool in your terminal (PowerShell or CMD) **without the `pixi` prefix and without the double dash `--`**.
*   **Default Executable Path**: `C:\Users\<Username>\AppData\Local\PaddlePDF\resources\paddle_pdf_backend\paddle_pdf_backend.exe`
*   **Examples**:
    ```bash
    # Navigate to the backend directory (or add it to your system PATH)
    cd "C:\Users\<Username>\AppData\Local\PaddlePDF\resources\paddle_pdf_backend"

    # Process PDF (CPU mode)
    paddle_pdf_backend.exe -i "D:\path\to\book.pdf"

    # Process PDF (GPU mode with specific model)
    paddle_pdf_backend.exe -gpu -model ch_plus -i "D:\path\to\book.pdf"
    ```

---

### 2. Command-Line Arguments

| Argument | Description | Default |
|---|---|---|
| `-i, --input` | **Required**, path to the input PDF file | — |
| `-gpu` | Enable GPU acceleration (requires CUDA setup) | Off |
| `-model <name>` | OCR model name (ch/ch_plus/ch_server_v2/en/...) | `ch` |
| `-o <dir>` | Output directory | `<filename>_ocr_output/` |
| `--max-pages N` | Maximum number of pages to process (0 = all) | 0 |
| `--dpi N` | PDF rendering resolution (300 default, 400 recommended for dense text) | 300 |
| `--conf` | Include confidence scores in output text file (.txt) | Off |
| `--angle-cls` | Enable text direction classification | On |
| `--no-angle-cls` | Disable text direction classification (slightly faster) | — |
| `--list-models` | List all available models and exit | — |
| `--force-redownload` | Force re-download of model files | — |
| `--diagnose` | Diagnose local GPU and CUDA environments and exit | — |
| `-v` | Verbose output | Off |

---

### 3. CLI Examples

#### ▌ System Diagnostics
```bash
# Check if local graphics card, CUDA, and cuDNN DLLs are configured correctly
paddle_pdf_backend.exe --diagnose
# (Development Env)
pixi run run -- --diagnose
```

#### ▌ List Available Models
```bash
paddle_pdf_backend.exe --list-models
# (Development Env)
pixi run run -- --list-models
```

#### ▌ Limit Pages & Custom Output
```bash
# Process only the first 5 pages for preview and save to a custom output directory
paddle_pdf_backend.exe -i "book.pdf" --max-pages 5 -o "D:\ocr_results"
# (Development Env)
pixi run run -- -i "book.pdf" --max-pages 5 -o "D:\ocr_results"
```

---

## Available Models

| Model | Language | Description | Recommended For |
|------|------|------|---|
| `ch` | Chinese, English | mobile slim (fastest) | **Default**, most Chinese PDFs |
| `ch_plus` | Chinese, English | server (more accurate) | Complex layouts, average print quality |
| `ch_server_v2` | Chinese, English | server v2 (most accurate) | Traditional text, classics, blurry scans |
| `en` | English | English only | English books, academic papers |
| `cyrillic` | Russian, etc. | Cyrillic script | Russian/Cyrillic PDFs |
| `japanese` | Japanese, Chinese | Japanese + Chinese | Japanese PDFs |
| `korean` | Korean, Chinese | Korean + Chinese | Korean PDFs |

---

## Output Files

After processing, two files are created in the output directory:

| File | Description |
|------|------|
| `<filename>_searchable.pdf` | PDF with transparent text layer. Copyable and Ctrl+F searchable |
| `<filename>_text.txt` | Plain text output containing recognized text (no confidence scores by default) |

### Text Output Format

Default mode (plain text):
```
OCR Result - Generated by pdf2txt
Model: ch
GPU: Yes
============================================================

--- Page 1 (14 lines, conf=89.6%) ---
  中國古典文學理論批評專著选辑
  詩品注

============================================================
Total lines: 67
Avg confidence: 72.4%
Pages processed: 5
```

With `--conf` (with confidence scores):
```
--- Page 1 (14 lines, conf=89.6%) ---
  中國古典文學理論批評專著选辑  [conf:95%]
  詩品注  [conf:92%]
  Blurry text  [conf:67%]
```

---

## GPU Acceleration Configuration

### Requirements

| Component | Description | Recommended/Required Version |
|---|---|---|
| NVIDIA GPU | RTX 3060+ (6GB+) recommended | CUDA Cores enabled |
| NVIDIA Driver | Needed to support CUDA 12.x | [Driver Downloads](https://www.nvidia.com/Download/index.aspx) |
| CUDA Toolkit | Core runtime library (Paddle is compiled with **CUDA 12.6**) | **12.6** (or 12.x compatible)<br>[CUDA Toolkit Archive](https://developer.nvidia.com/cuda-toolkit-archive) |
| cuDNN | Deep learning acceleration library, merged into CUDA path | **v9.x** (or v8.x matching CUDA 12.x)<br>[cuDNN Downloads](https://developer.nvidia.com/cudnn) |

### Step-by-Step Installation Guide

#### 1. Install/Update Graphics Driver
1. Visit the [NVIDIA Driver Downloads site](https://www.nvidia.com/Download/index.aspx).
2. Choose your GPU model, download the latest driver, and run the installation.

#### 2. Install CUDA Toolkit (e.g., CUDA 12.6)
1. Go to the [CUDA 12.6 Download Page](https://developer.nvidia.com/cuda-12-6-0-download-archive).
2. Select Windows -> x86_64 -> corresponding OS version -> exe (local) and click download.
3. Run the installer and choose "Express installation (Recommended)". The installer will set the `CUDA_PATH` environment variable and append the binary path to your system's `Path` (typically installed at `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6`).

#### 3. Install cuDNN Library
PaddleOCR requires cuDNN to achieve hardware acceleration:
1. Visit the [NVIDIA cuDNN page](https://developer.nvidia.com/cudnn) (registration/login required).
2. Download the cuDNN Windows (x64) zip package matching CUDA 12.x.
3. Extract the zip. Copy **all files** inside `bin/`, `include/`, and `lib/` and paste (merge) them into the corresponding folders of your CUDA Toolkit installation path (e.g., `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\`). Replace any duplicate files if prompted.

#### 4. Verify Environment Paths
1. Open terminal and run `nvcc -V`. If it prints `release 12.6`, the CUDA compiler is ready.
2. Ensure the CUDA Toolkit `bin` path is present in your system's `Path` environment variable.
3. To verify GPU acceleration in the **development environment**, run:
   ```bash
   pixi run check-gpu
   ```

---

## Performance Reference

Test environment: Intel i7-10870H + NVIDIA RTX 3060 Laptop (6GB)

| Mode | Model | DPI | Time per Page |
|---|---|---|---|
| CPU | ch | 300 | 15-20s |
| GPU | ch | 300 | 3-5s |
| GPU | ch_plus | 300 | 8-12s |
| GPU | ch_server_v2 | 300 | 15-25s |

---

## Troubleshooting

### Garbled Recognition Results / Copy Shows Gibberish

- **Copying text from the PDF shows `???` question marks in Notepad**:
  This issue has been fully fixed in the latest version. The software embeds a complete Unicode mapping table (ToUnicode) and local CJK fonts (e.g. `simsun.ttc` on Windows) into the PDF. If your OS lacks common Chinese fonts, it automatically falls back to the built-in `cjk` font library.
- **OCR errors or blurry text**:
  - Resolution too low: Try increasing the render DPI by adding `--dpi 400` and run again.
  - Model accuracy insufficient: For vertical text, traditional CJK, or classical layouts, use `--model ch_server_v2`.

### Text Selection Highlight Misaligned / Drifting

- **Selection highlight doesn't align with background text**:
  The latest version introduces **glyph physical width matching and vertical centering algorithm** to ensure tight overlay alignment.
  - If there's still minor pixel-level drift, it is usually due to rough boxes from the OCR engine. Try increasing resolution by adding `--dpi 400`.

### Out of Memory (OOM)

- For large resolution or long PDFs:
  - Lower the DPI: Use `--dpi 200` to run.
  - Limit pages: Use `--max-pages 20` to process in smaller batches.

### Model Download Failed

- Re-run on command line, or pass the force-download argument:
  ```bash
  paddle_pdf_backend.exe -i "book.pdf" --force-redownload
  ```
- Cache folders:
  - `~/.paddleocr/` — PaddleOCR core models
  - `~/.paddlex/` — PaddleX models
