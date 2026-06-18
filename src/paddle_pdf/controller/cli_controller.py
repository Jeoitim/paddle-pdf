"""CLI controller — argparse interface, replaces the old main.py."""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

from ..common.schemas import OcrOptions, TaskStatus
from ..service.ocr_service import OcrService
from ..service.model_service import ModelService
from ..service.system_service import SystemService


def build_argparser() -> argparse.ArgumentParser:
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

  python -m paddle_pdf -i "book.pdf"      # Alternative invocation
        """,
    )
    parser.add_argument(
        "-gpu", "--gpu", action="store_true",
        help="use GPU for OCR (requires CUDA-enabled paddlepaddle-gpu)",
    )
    parser.add_argument(
        "-model", "--model", default="ch",
        help="OCR model name (default: ch). Use --list-models to see all options.",
    )
    parser.add_argument(
        "-i", "--input", help="input PDF file path (required unless --list-models)",
    )
    parser.add_argument(
        "-o", "--output",
        help="output directory (default: <input>_ocr_output/ in same dir as input)",
    )
    parser.add_argument(
        "--max-pages", type=int, default=0,
        help="maximum number of pages to process (0 = all pages, default: 0)",
    )
    parser.add_argument(
        "--dpi", type=int, default=300,
        help="DPI for PDF page rendering (default: 300, recommended: 400 for dense text)",
    )
    parser.add_argument(
        "--angle-cls", action="store_true", default=True,
        help="enable angle classification for rotated text (default: True)",
    )
    parser.add_argument(
        "--no-angle-cls", dest="angle_cls", action="store_false",
        help="disable angle classification (faster but may miss rotated text)",
    )
    parser.add_argument(
        "--conf", action="store_true",
        help="include confidence scores in text output (default: plain text only)",
    )
    parser.add_argument(
        "--list-models", action="store_true",
        help="list all available OCR models and exit",
    )
    parser.add_argument(
        "--force-redownload", action="store_true",
        help="force re-download of the OCR model",
    )
    parser.add_argument(
        "--diagnose", action="store_true",
        help="run GPU/environment diagnostics and exit",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="show detailed progress and timing",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    return parser


def _size_human(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024  # type: ignore[assignment]
    return f"{size_bytes:.1f} TB"


def main() -> int:
    """CLI entry point."""
    parser = build_argparser()
    args = parser.parse_args()

    # --list-models
    if args.list_models:
        model_svc = ModelService()
        print("Available OCR Models:")
        print("=" * 60)
        for m in model_svc.list_models():
            marker = " (DEFAULT)" if m.name == "ch" else ""
            cached = " [cached]" if m.cached else ""
            print(f"  {m.name:<18} [{m.lang}] {m.desc}{marker}{cached}")
            if m.note:
                print(f"                      Note: {m.note}")
        print()
        print("Default model: ch")
        print("Usage: pdf2txt -model=<name> -i <file>")
        return 0

    # --diagnose
    if args.diagnose:
        sys_svc = SystemService()
        print("GPU / Environment Diagnostics")
        print("=" * 40)
        info = sys_svc.check_gpu()
        print(f"  GPU available:   {info.available}")
        print(f"  CUDA version:    {info.cuda_version or 'N/A'}")
        print(f"  CUDA root:       {info.cuda_root or 'N/A'}")
        print(f"  Device count:    {info.device_count}")
        if info.error:
            print(f"  Error:           {info.error}")
        print()
        diag = sys_svc.diagnose()
        for k, v in diag.items():
            print(f"  {k}: {v}")
        return 0

    # Validate input
    if not args.input:
        parser.error("-i/--input is required (unless using --list-models)")
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}", file=sys.stderr)
        return 1
    if input_path.suffix.lower() != ".pdf":
        print(f"[ERROR] Input file must be a PDF: {input_path}", file=sys.stderr)
        return 1

    file_size = _size_human(input_path.stat().st_size)
    print(f"[INFO] Input:  {input_path.name} ({file_size})")

    output_dir = Path(args.output).resolve() if args.output else None

    model_name = args.model.lower().strip("'\"")
    from ..core.models import MODEL_REGISTRY, get_model_info

    if model_name not in MODEL_REGISTRY:
        print(f"[ERROR] Unknown model: '{model_name}'", file=sys.stderr)
        print("[ERROR] Use --list-models to see available options.", file=sys.stderr)
        return 1

    options = OcrOptions(
        model_name=model_name,
        use_gpu=args.gpu,
        dpi=args.dpi,
        max_pages=args.max_pages if args.max_pages > 0 else None,
        angle_cls=args.angle_cls,
        show_confidence=args.conf,
    )

    print(f"[INFO] Model:  {model_name} ({get_model_info(model_name)['desc']})")
    print(f"[INFO] DPI:    {args.dpi}")
    print(f"[INFO] GPU:    {'Yes' if args.gpu else 'No (CPU)'}")
    print(f"[INFO] Angle classification: {'On' if args.angle_cls else 'Off'}")
    if args.max_pages > 0:
        print(f"[INFO] Pages:  {args.max_pages} (preview mode)")
    print()

    # Force redownload if requested
    if args.force_redownload:
        ModelService().download(model_name, force=True)

    # Progress callback for CLI
    last_pct = [0]

    def _cli_progress(tp):
        if tp.status == TaskStatus.OCR_RUNNING and tp.total_pages > 0:
            pct = int(tp.current_page / tp.total_pages * 100)
            if pct >= last_pct[0] + 10 or pct == 100:
                print(
                    f"      Progress: {pct}% ({tp.current_page}/{tp.total_pages} pages)"
                )
                last_pct[0] = pct
        elif tp.message:
            print(f"      {tp.message}")

    # Run
    print("=" * 50)
    ocr_svc = OcrService()

    try:
        result = ocr_svc.process_pdf(
            input_path=input_path,
            options=options,
            output_dir=output_dir,
            progress_callback=_cli_progress,
        )
    except KeyboardInterrupt:
        print("\n[WARN] Interrupted by user", file=sys.stderr)
        ocr_svc.cancel()
        return 130
    except Exception as e:
        print(f"[ERROR] Processing failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    # Summary
    print()
    print("=" * 50)
    print(f"Complete! ({result.elapsed_seconds:.1f}s)")
    print(f"  {result.output_pdf_path}")
    print(f"  {result.output_txt_path}")
    print(f"  Pages processed: {result.total_pages}")
    print(f"  Text lines found: {result.total_lines}")
    if result.avg_confidence > 0:
        print(f"  Avg confidence:   {result.avg_confidence:.1f}%")
    print()
    return 0
