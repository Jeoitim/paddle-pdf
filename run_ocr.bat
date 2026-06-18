@echo off
:: PDF OCR CLI - Batch Launcher (pixi-based)
:: Usage: run_ocr.bat [options] -i <input.pdf>
:: Options:
::   -gpu          Use GPU mode (requires CUDA Toolkit)
::   -model=xxx    Specify OCR model (ch, ch_plus, ch_server_v2, en, ...)
::   -o=dir        Output directory
::   --max-pages N Limit pages
::   --dpi N       DPI (default: 300)
::   --list-models Show available models
::
:: Examples:
::   run_ocr.bat -i "book.pdf"
::   run_ocr.bat -gpu -i "book.pdf"
::   run_ocr.bat -gpu -model=ch_plus -i "book.pdf"
::   run_ocr.bat -i "book.pdf" -o "./output"
::   run_ocr.bat -i "book.pdf" --max-pages 5
::   run_ocr.bat --list-models

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"

:: Detect GPU mode flag
set "GPU_MODE="

echo %* | findstr /i "\-gpu" >nul
if not errorlevel 1 (
    set "GPU_MODE=1"
)

:: Auto-configure CUDA environment for GPU mode
if defined GPU_MODE (
    set "CUDA_FOUND="
    for /d %%D in ("C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v*") do (
        if exist "%%D\bin\x64\cudart64_*.dll" (
            set "CUDA_DLL_PATH=%%D\bin\x64"
            set "CUDA_HOME=%%D"
            set "CUDA_FOUND=1"
        ) else if exist "%%D\bin\cudart64_*.dll" (
            set "CUDA_DLL_PATH=%%D\bin"
            set "CUDA_HOME=%%D"
            set "CUDA_FOUND=1"
        )
    )

    if defined CUDA_FOUND (
        echo [GPU] CUDA runtime: !CUDA_DLL_PATH!
        set "PATH=!CUDA_DLL_PATH!;!PATH!"
        set "CUDA_PATH=!CUDA_HOME!"
    ) else (
        echo [GPU] Warning: CUDA runtime DLLs not found. GPU mode may not work.
        echo [GPU] If GPU count is 0, install CUDA 12.x Runtime:
        echo [GPU]   https://developer.nvidia.com/cuda-downloads
    )
)

:: Run via pixi
pixi run python "%SCRIPT_DIR%main.py" %*

exit /b %ERRORLEVEL%
