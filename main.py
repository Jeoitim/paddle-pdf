#!/usr/bin/env python3
"""
PDF OCR CLI Tool
Usage:
    main.py -i <input.pdf> [options]
    main.py -gpu -model=ch -i <input.pdf>
    main.py -i <input.pdf> -o <output_dir>

Examples:
    main.py -i "book.pdf"
    main.py -gpu -i "book.pdf"
    main.py -gpu -model=ch_server_v2 -i "book.pdf"
    main.py -i "book.pdf" --max-pages 5
    main.py -i "book.pdf" -o "./output_folder"
    main.py -i "book.pdf" --dpi 400
    main.py -i "book.pdf" --conf
"""

import sys
import os
import argparse
import time
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ocr_engine import PaddleOCREngine
from pdf_pipeline import PDFProcessor
from models import (
    MODEL_REGISTRY,
    get_model_info,
    get_model_dir,
    list_models,
    download_model,
)


def parse_args():
    parser = argparse.ArgumentParser(
        prog="pdf2txt",
        description="PDF OCR CLI Tool powered by PaddleOCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Model Options:
  Available models (default: ch, ch_plus, en):
    ch               Chinese, English (mobile slim, fastest)
    ch_plus          Chinese, English (server, more accurate)
    ch_server_v2     Chinese, English (latest server, best accuracy)
    en               English only
    cyrillic         Cyrillic languages
    japanese         Japanese, Chinese
    korean           Korean, Chinese

Usage Examples:
  pdf2txt -i "book.pdf"                    # CPU mode, default model
  pdf2txt -gpu -i "book.pdf"              # GPU mode, default model
  pdf2txt -gpu -model=ch_plus -i "b.pdf"  # GPU mode, specific model
  pdf2txt -i "b.pdf" -o "./output"        # Custom output dir
  pdf2txt -i "b.pdf" --max-pages 10      # First 10 pages only
  pdf2txt -i "b.pdf" --dpi 400           # Higher resolution
  pdf2txt -i "b.pdf" --conf              # Show confidence scores
  pdf2txt --list-models                   # Show all available models

  python main.py -i "book.pdf"            # Alternative invocation
        """,
    )
    parser.add_argument(
        "-gpu",
        "--gpu",
        action="store_true",
        help="use GPU for OCR (requires CUDA-enabled paddlepaddle-gpu)",
    )
    parser.add_argument(
        "-model",
        "--model",
        default="ch",
        help="OCR model name (default: ch). Use --list-models to see all options.",
    )
    parser.add_argument(
        "-i", "--input", required=True, help="input PDF file path (required)"
    )
    parser.add_argument(
        "-o",
        "--output",
        help="output directory (default: <input>_ocr_output/ in same dir as input)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="maximum number of pages to process (0 = all pages, default: 0)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI for PDF page rendering (default: 300, recommended: 400 for dense text)",
    )
    parser.add_argument(
        "--angle-cls",
        action="store_true",
        default=True,
        help="enable angle classification for rotated text (default: True)",
    )
    parser.add_argument(
        "--no-angle-cls",
        dest="angle_cls",
        action="store_false",
        help="disable angle classification (faster but may miss rotated text)",
    )
    parser.add_argument(
        "--conf",
        action="store_true",
        help="include confidence scores in text output (default: plain text only)",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="list all available OCR models and exit",
    )
    parser.add_argument(
        "--force-redownload",
        action="store_true",
        help="force re-download of the OCR model",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="show detailed progress and timing"
    )
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    return parser.parse_args()


def get_file_size_human(size_bytes):
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def main():
    args = parse_args()

    # List models and exit
    if args.list_models:
        print("Available OCR Models:")
        print("=" * 60)
        for name, info in MODEL_REGISTRY.items():
            desc = info["desc"]
            lang = info["lang"]
            note = info.get("note", "")
            marker = " (DEFAULT)" if name == "ch" else ""
            print(f"  {name:<18} [{lang}] {desc}{marker}")
            if note:
                print(f"                      Note: {note}")
        print()
        print(f"Default model: ch")
        print(f"Usage: pdf2txt -model=<name> -i <file>")
        return 0

    # Resolve input path
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}", file=sys.stderr)
        return 1
    if not input_path.suffix.lower() == ".pdf":
        print(f"[ERROR] Input file must be a PDF: {input_path}", file=sys.stderr)
        return 1

    file_size = get_file_size_human(input_path.stat().st_size)
    print(f"[INFO] Input:  {input_path.name} ({file_size})")

    # Determine output directory
    if args.output:
        output_dir = Path(args.output).resolve()
    else:
        output_dir = input_path.parent / f"{input_path.stem}_ocr_output"

    temp_dir = output_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Output: {output_dir}/")

    # Validate model
    model_name = args.model.lower().strip("'\"")

    # Check if model is in registry
    if model_name not in MODEL_REGISTRY:
        print(f"[ERROR] Unknown model: '{model_name}'", file=sys.stderr)
        print(f"[ERROR] Use --list-models to see available options.", file=sys.stderr)
        return 1

    # Initialize OCR engine
    print(f"[INFO] Model:  {model_name} ({get_model_info(model_name)['desc']})")
    print(f"[INFO] DPI:   {args.dpi}")
    print(f"[INFO] GPU:    {'Yes' if args.gpu else 'No (CPU)'}")
    print(f"[INFO] Angle classification: {'On' if args.angle_cls else 'Off'}")
    if args.max_pages > 0:
        print(f"[INFO] Pages:  {args.max_pages} (preview mode)")
    print()

    try:
        engine = PaddleOCREngine(
            use_gpu=args.gpu,
            model_name=model_name,
            use_angle_cls=args.angle_cls,
            verbose=args.verbose,
        )
    except Exception as e:
        print(f"[ERROR] Failed to initialize OCR engine: {e}", file=sys.stderr)
        return 1

    # Check GPU availability if requested
    if args.gpu:
        gpu_ok = engine.check_gpu()
        if gpu_ok:
            print(f"[OK]   GPU detected and working")
        else:
            print(f"[WARN] GPU requested but not available. Falling back to CPU.")
            args.gpu = False
            # Re-init in CPU mode
            engine = PaddleOCREngine(
                use_gpu=False,
                model_name=model_name,
                use_angle_cls=args.angle_cls,
                verbose=args.verbose,
            )
    print()

    # Download model if needed
    model_dir = get_model_dir(model_name)

    if args.force_redownload or not engine.is_model_available(model_name):
        print(f"[INFO] Downloading model '{model_name}'...")
        ok = download_model(model_name, force=args.force_redownload)
        if not ok:
            print(
                f"[ERROR] Failed to download model '{model_name}'. "
                f"The model may not exist.",
                file=sys.stderr,
            )
            return 1
        print(f"[OK]   Model downloaded: {model_dir}")
    else:
        print(f"[OK]   Model ready: {model_dir}")
    print()

    # Process PDF
    print("=" * 50)
    t0 = time.time()

    try:
        processor = PDFProcessor(
            ocr_engine=engine,
            dpi=args.dpi,
            max_pages=args.max_pages if args.max_pages > 0 else None,
            temp_dir=temp_dir,
            verbose=args.verbose,
        )

        print(f"[1/3] Extracting pages from PDF...")
        pdf_info = processor.extract_pages(input_path)
        print(f"      {pdf_info['total_pages']} pages found")
        if pdf_info.get("encrypted"):
            print(f"[WARN] PDF is encrypted, may have limited OCR results")

        print(f"[2/3] Running OCR on {len(pdf_info['pages'])} page(s)...")
        ocr_result = processor.run_ocr(
            pdf_info["pages"],
            progress_callback=_make_progress_callback(pdf_info["total_pages"]),
        )

        print(f"[3/3] Generating output files...")
        output_files = processor.save_output(
            ocr_result=ocr_result,
            input_pdf=input_path,
            output_dir=output_dir,
            show_conf=args.conf,
        )

    except KeyboardInterrupt:
        print(f"\n[WARN] Interrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[ERROR] Processing failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1
    finally:
        # Cleanup temp files
        if temp_dir.exists() and any(temp_dir.iterdir()):
            try:
                shutil.rmtree(temp_dir)
                print(f"[CLEAN] Temp files removed")
            except Exception:
                pass

    elapsed = time.time() - t0

    # Summary
    print()
    print("=" * 50)
    print(f"Complete! ({elapsed:.1f}s)")
    print(f"  {output_files['pdf']}")
    print(f"  {output_files['txt']}")

    if "stats" in ocr_result and ocr_result["stats"]:
        stats = ocr_result["stats"]
        pages_done = stats.get("pages_processed", 0)
        total_lines = stats.get("total_lines", 0)
        avg_conf = stats.get("avg_confidence", 0)
        print(f"  Pages processed: {pages_done}")
        print(f"  Text lines found: {total_lines}")
        if avg_conf > 0:
            print(f"  Avg confidence:   {avg_conf:.1f}%")

    print()
    return 0


def _make_progress_callback(total_pages):
    last_pct = 0

    def callback(page_num, lines, elapsed):
        nonlocal last_pct
        pct = int(page_num / total_pages * 100)
        if pct >= last_pct + 10 or pct == 100:
            print(
                f"      Progress: {pct}% ({page_num}/{total_pages} pages, {elapsed:.1f}s/page)"
            )
            last_pct = pct

    return callback


if __name__ == "__main__":
    sys.exit(main())
