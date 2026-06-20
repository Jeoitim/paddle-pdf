# User Guide

## ⚠️ Important: Searchable PDF Quality Expectations

The positioning accuracy of the searchable text layer depends heavily on:

- **Layout complexity**: Simpler layouts (single column, no mixed text/images) produce better results
- **Source file clarity**: Higher quality scans/photos lead to more accurate OCR and tighter text alignment
- **Model size**: Larger models (e.g., `ch_server_v2`) significantly outperform lightweight ones

If the source file quality is mediocre, a smaller model is used, or CUDA acceleration is unavailable, the experience degrades significantly. **Do not expect out-of-the-box accuracy** — choose the appropriate model and DPI settings based on your needs.

## Quick Start

We provide two separate installation and usage routes for different types of users:

### Installation Guide

#### 1. For General Users (Recommended, One-Click Installation)
General users **do not** need to install Git, Python, Node.js, Pixi, or C++ compiler environments:
1. Go to the [Releases page](https://github.com/Jeoitim/paddle_pdf/releases) and download the latest pre-packaged installer (e.g., `PaddlePDF_1.0.0_x64-setup.exe`).
2. Double-click the installer and follow the instructions to complete setup. Once installed, you can launch the graphical user interface (GUI) from your desktop shortcut.

#### 2. For Developers (Local Source & Development)
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

### Basic Usage

#### Development Environment (Pixi)

```bash
# CPU mode
pixi run run -- -i "book.pdf"

# GPU mode
pixi run run-gpu -- -i "book.pdf"

# Or use the batch script (Windows)
run_ocr.bat -i "book.pdf"
run_ocr.bat -gpu -i "book.pdf"
```

#### Production Environment (Packaged Version)

After compiling/installing, the backend engine `paddle_pdf_backend.exe` is fully compiled and runs independently of local Python environment dependencies. You can use it directly as a standalone CLI tool in your terminal (PowerShell or CMD):

1. **Executable Path**:
   - Installed path: `C:\Users\<Username>\AppData\Local\PaddlePDF\resources\paddle_pdf_backend\paddle_pdf_backend.exe`
   - Or in the compiled build folder: `resources\paddle_pdf_backend\paddle_pdf_backend.exe`

2. **Usage Examples**:
   ```bash
   # Navigate to the backend directory (or add it to your system PATH)
   cd "C:\Users\<Username>\AppData\Local\PaddlePDF\resources\paddle_pdf_backend"

   # 1. Diagnose system environment and GPU/CUDA setup
   paddle_pdf_backend.exe --diagnose

   # 2. List all available OCR models
   paddle_pdf_backend.exe --list-models

   # 3. Process a PDF in CPU mode (outputs are generated under the input PDF folder)
   paddle_pdf_backend.exe -i "D:\path\to\book.pdf"

   # 4. Process a PDF in GPU mode with a specific model
   paddle_pdf_backend.exe -gpu -model ch_plus -i "D:\path\to\book.pdf"
   ```

## Command-Line Arguments

| Argument | Description | Default |
|---|---|---|
| `-i, --input` | **Required**, input PDF file path | — |
| `-gpu` | Enable GPU acceleration | Off |
| `-model <name>` | OCR model | `ch` |
| `-o <dir>` | Output directory | `<input_filename>_ocr_output/` |
| `--max-pages N` | Max pages to process (0=all) | 0 |
| `--dpi N` | PDF render resolution | 300 |
| `--conf` | Include confidence in text output | Off |
| `--angle-cls` | Enable text direction classification | On |
| `--no-angle-cls` | Disable direction classification (faster) | — |
| `--list-models` | List all available models | — |
| `--force-redownload` | Force re-download models | — |
| `-v` | Verbose output | Off |

## Usage Examples

### Basic OCR

```bash
# Default Chinese model, CPU mode
pixi run run -- -i "document.pdf"

# GPU acceleration
pixi run run-gpu -- -i "document.pdf"
```

### Specifying Models

```bash
# High-accuracy model
pixi run run-gpu -- -gpu -model=ch_plus -i "document.pdf"

# Highest accuracy (for classical texts, vertical layout)
pixi run run-gpu -- -gpu -model=ch_server_v2 -i "classics.pdf" --dpi 400

# List all models
pixi run run -- --list-models
```

### Limiting Pages

```bash
# Process only the first 5 pages (preview)
pixi run run -- -i "large_file.pdf" --max-pages 5
```

### Custom Output

```bash
# Specify output directory
pixi run run -- -i "document.pdf" -o "./output"

# Include confidence scores in output
pixi run run -- -i "document.pdf" --conf
```

### Using Batch Scripts (Windows)

```bash
run_ocr.bat -i "book.pdf"
run_ocr.bat -gpu -i "book.pdf"
run_ocr.bat -gpu -model=ch_plus -i "book.pdf" --max-pages 10
run_ocr.bat -i "book.pdf" --conf
run_ocr.bat --list-models
```

## Available Models

| Model | Language | Description | Recommended For |
|---|---|---|---|
| `ch` | Chinese, English | mobile slim (fastest) | **Default**, most Chinese PDFs |
| `ch_plus` | Chinese, English | server (more accurate) | Complex layouts, average print quality |
| `ch_server_v2` | Chinese, English | server v2 (most accurate) | Vertical traditional text, classics, blurry scans |
| `en` | English | English only | English books, papers |
| `cyrillic` | Russian, etc. | Cyrillic script | Russian PDFs |
| `japanese` | Japanese, Chinese | Japanese + Chinese | Japanese PDFs |
| `korean` | Korean, Chinese | Korean + Chinese | Korean PDFs |

## Output Files

After processing, the following files are generated in the output directory:

| File | Description |
|---|---|
| `<filename>_searchable.pdf` | PDF with text layer, Ctrl+F searchable, Ctrl+C copyable |
| `<filename>_text.txt` | Plain text output, confidence scores off by default (use `--conf` to enable) |

### Text Output Format

Default mode (plain text):
```
OCR Result - Generated by pdf2txt
Model: ch
GPU: Yes
============================================================

--- Page 1 (14 lines, conf=89.6%) ---
  Sample recognized text line 1
  Sample recognized text line 2

============================================================
Total lines: 67
Avg confidence: 72.4%
Pages processed: 5
```

With `--conf` (with confidence scores):
```
--- Page 1 (14 lines, conf=89.6%) ---
  Sample text line 1  [conf:95%]
  Sample text line 2  [conf:92%]
  Blurry text  [conf:67%]
```

## Task Queue (GUI Batch Processing)

The GUI supports a task queue that lets you add multiple PDF files consecutively, processing them one by one in the background:

### How to Use

1. After dragging in or selecting PDF files, tasks are automatically added to the queue
2. Waiting tasks appear in the **Queue** section, running tasks in the **Processing** section
3. Each task can be individually **cancelled** (queued tasks are removed directly, running tasks are interrupted)
4. Completed/failed/cancelled tasks appear in the **Finished** section and can be removed individually or cleared all at once

### Task Status

| Status | Description |
|---|---|
| `pending` | Waiting in queue |
| `extracting` / `ocr_running` / `saving` | Currently processing |
| `completed` | Processing complete |
| `failed` | Processing failed (error message available) |
| `cancelled` | Cancelled |

### Notes

- Tasks run **sequentially** by default (`max_workers=1`), as GPU memory rarely allows concurrent models
- Each task uses its own `OcrService` instance with isolated model state
- Cancellation: queued tasks are skipped directly; running tasks are interrupted via `InterruptedError`
- After task completion, the frontend receives full result data via the `task://completed` event

## GPU Acceleration

### Requirements

| Component | Description | Recommended/Required Version |
|---|---|---|
| NVIDIA GPU | RTX 3060+ (6GB+) recommended | CUDA Cores enabled |
| NVIDIA Driver | Needed to support CUDA 12.x | [Driver Downloads](https://www.nvidia.com/Download/index.aspx) |
| CUDA Toolkit | Core runtime library (Paddle is compiled with **CUDA 12.6**) | **12.6** (or 12.x compatible)<br>[CUDA Toolkit Archive](https://developer.nvidia.com/cuda-toolkit-archive) |
| cuDNN | Deep learning acceleration library, merged into CUDA path | **v9.x** (or v8.x matching CUDA 12.x)<br>[cuDNN Downloads](https://developer.nvidia.com/cudnn) |

### NVIDIA Toolchain Installation Guide

#### 1. Install/Update Graphics Driver
1. Visit the [NVIDIA Driver Downloads site](https://www.nvidia.com/Download/index.aspx).
2. Choose your GPU model, download the latest driver, and run the installation.

#### 2. Install CUDA Toolkit (e.g., CUDA 12.6)
1. Go to the [CUDA 12.6 Download Page](https://developer.nvidia.com/cuda-12-6-0-download-archive) (or select 12.6 from the [CUDA Toolkit Archive](https://developer.nvidia.com/cuda-toolkit-archive)).
2. Select your OS platform (Windows -> x86_64 -> 10 or 11 -> exe (local)) and click download.
3. Run the installer and choose "Express installation (Recommended)". The installer will set the `CUDA_PATH` environment variable and append the binary path to your system's `Path` (typically installed at `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6`).

#### 3. Install cuDNN Library
PaddleOCR requires cuDNN to achieve hardware acceleration on NVIDIA GPUs:
1. Visit the [NVIDIA cuDNN page](https://developer.nvidia.com/cudnn). Sign in or register for a free developer account if required.
2. Download the cuDNN zip archive matching your CUDA version (e.g. cuDNN for CUDA 12.x, Windows (x64) zip package).
3. Extract the downloaded zip. Inside, you will see `bin/`, `include/`, and `lib/` folders.
4. Copy **all files** from these folders and paste (merge) them into the corresponding directories of your CUDA Toolkit installation path (e.g. `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\`).
   *If prompted to overwrite existing files, select Yes.*

#### 4. Verify Environmental Paths
1. Open terminal (or PowerShell/cmd) and type the following command to check if the CUDA compiler is available:
   ```bash
   nvcc -V
   ```
   It should output `release 12.6`.
2. Make sure `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin` is present in your system's environment `Path` variable.

### Verify GPU

```bash
pixi run check-gpu
```

### Common GPU Issues

**GPU detection returns 0**:
1. Check `nvcc -V` output to verify CUDA compiler presence and system `Path` configuration.
2. Verify that cuDNN library files (such as `cudnn64_*.dll` or `cudnn_ops_infer64_*.dll`) were successfully copied into the `bin/` subfolder of your CUDA installation path.
3. Restart your computer to ensure newly configured environment variables are applied.

## Performance Reference

Test environment: Intel i7-10870H + NVIDIA RTX 3060 Laptop (6GB)

| Mode | Model | DPI | Time per Page |
|---|---|---|---|
| CPU | ch | 300 | 15-20s |
| GPU | ch | 300 | 3-5s |
| GPU | ch_plus | 300 | 8-12s |
| GPU | ch_server_v2 | 300 | 15-25s |

## Troubleshooting

### Garbled Recognition Results / Copy Shows Gibberish

*   **Copying text from the PDF shows `???` question marks in Notepad/Edge**:
    This issue has been fully fixed in the latest version. The software embeds a complete Unicode character mapping table (ToUnicode) and local CJK font files (e.g., `simsun.ttc` on Windows) into the PDF. If your OS lacks common Chinese fonts, the program will automatically fall back to the built-in `cjk` font library. Ensure at least one Chinese font is installed on your system.
*   **OCR recognition has typos or fails to recognize**:
    *   PDF page resolution is too low: Try increasing resolution by adding `--dpi 400` (default is 300) and re-running.
    *   Model accuracy is insufficient: Use `-model=ch_plus` or the highest-accuracy `-model=ch_server_v2` for traditional text, classics, or handwriting.

### Text Selection Highlight Misaligned / Drifting / Line Wrapping

*   **Selection highlight doesn't align with background text**:
    The latest version introduces **glyph physical width matching and vertical centering algorithm**, so the text layer is now highly aligned with the underlying image text.
    *   If there's still slight pixel-level drift, it's mainly because the bounding boxes returned by the OCR model aren't precise enough at low resolutions. You can fix this by increasing the render DPI, e.g., adding `--dpi 400`.
    *   Very few fonts with unusual kerning may have slight offsets, but this doesn't affect search or full-line text copying.

### Out of Memory (OOM)

*   When processing very high-resolution PDFs or long documents, you may encounter out-of-memory errors:
    *   Lower the DPI: Use `--dpi 200` (faster, but slightly reduces accuracy).
    *   Process in batches: Use `--max-pages 20` to limit the number of pages processed at once.

### Encrypted PDF Cannot Be Processed

Use another tool to remove the password protection first, then run OCR.

### Model Download Failed

```bash
# Force re-download
pixi run run -- -i "book.pdf" --force-redownload
```

Model cache locations:
- `~/.paddleocr/` — PaddleOCR models
- `~/.paddlex/` — PaddleX models
