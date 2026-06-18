"""OCR task orchestration — the primary business service."""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Any, Callable

from ..common.schemas import OcrOptions, TaskProgress, TaskResult, TaskStatus, PageResult
from ..core.ocr_engine import PaddleOCREngine
from ..core.pdf_pipeline import PDFProcessor

logger = logging.getLogger(__name__)


class OcrService:
    """Orchestrates the full PDF → OCR → output pipeline."""

    def __init__(self) -> None:
        self._engine: PaddleOCREngine | None = None
        self._cancelled = False

    def process_pdf(
        self,
        input_path: Path,
        options: OcrOptions,
        output_dir: Path | None = None,
        progress_callback: Callable[[TaskProgress], None] | None = None,
    ) -> TaskResult:
        """Run the complete OCR pipeline with progress reporting."""
        self._cancelled = False
        t0 = time.time()

        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        if input_path.suffix.lower() != ".pdf":
            raise ValueError(f"Input file must be a PDF: {input_path}")

        if output_dir is None:
            output_dir = input_path.parent / f"{input_path.stem}_ocr_output"
        temp_dir = output_dir / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        def _emit(status: TaskStatus, page: int = 0, total: int = 0, msg: str = ""):
            if progress_callback and not self._cancelled:
                progress_callback(
                    TaskProgress(
                        status=status,
                        current_page=page,
                        total_pages=total,
                        message=msg,
                        elapsed=time.time() - t0,
                    )
                )

        try:
            # Initialize engine
            _emit(TaskStatus.EXTRACTING, msg="Initializing OCR engine...")
            self._engine = PaddleOCREngine(
                use_gpu=options.use_gpu,
                model_name=options.model_name,
                use_angle_cls=options.angle_cls,
            )

            if options.use_gpu:
                if not self._engine.check_gpu():
                    logger.warning("GPU not available, falling back to CPU")
                    self._engine = PaddleOCREngine(
                        use_gpu=False,
                        model_name=options.model_name,
                        use_angle_cls=options.angle_cls,
                    )

            # Download model if needed
            if not self._engine.is_model_available(options.model_name):
                _emit(TaskStatus.EXTRACTING, msg=f"Downloading model '{options.model_name}'...")

            # Extract pages
            _emit(TaskStatus.EXTRACTING, msg="Extracting pages...")
            processor = PDFProcessor(
                ocr_engine=self._engine,
                dpi=options.dpi,
                max_pages=options.max_pages,
                temp_dir=temp_dir,
            )
            pdf_info = processor.extract_pages(input_path)
            total_pages = pdf_info["total_pages"]

            # OCR
            _emit(TaskStatus.OCR_RUNNING, page=0, total=total_pages, msg="Running OCR...")

            def _ocr_progress(page_num: int, lines: int, elapsed: float):
                if self._cancelled:
                    raise InterruptedError("Task cancelled")
                _emit(
                    TaskStatus.OCR_RUNNING,
                    page=page_num,
                    total=total_pages,
                    msg=f"Page {page_num}/{total_pages}",
                )

            ocr_result = processor.run_ocr(
                pdf_info["pages"], progress_callback=_ocr_progress
            )

            # Save output
            _emit(TaskStatus.SAVING, msg="Generating output files...")
            output_files = processor.save_output(
                ocr_result=ocr_result,
                input_pdf=input_path,
                output_dir=output_dir,
                show_conf=options.show_confidence,
            )

            # Cleanup temp
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass

            elapsed = time.time() - t0
            stats = ocr_result.get("stats", {})

            # Build PageResult list
            page_results = [
                PageResult(
                    page_num=r["page_num"],
                    image_path=r.get("image_path", ""),
                    ocr_results=r.get("lines", []),
                    num_lines=r.get("num_lines", 0),
                    avg_confidence=r.get("avg_confidence", 0.0),
                    elapsed=r.get("elapsed", 0.0),
                    error=r.get("error"),
                )
                for r in ocr_result.get("pages", [])
            ]

            result = TaskResult(
                input_path=input_path,
                output_pdf_path=output_files.get("pdf"),
                output_txt_path=output_files.get("txt"),
                total_pages=stats.get("pages_processed", 0),
                total_lines=stats.get("total_lines", 0),
                avg_confidence=stats.get("avg_confidence", 0.0),
                elapsed_seconds=elapsed,
                pages=page_results,
            )

            _emit(TaskStatus.COMPLETED, msg="Done!")
            return result

        except InterruptedError:
            _emit(TaskStatus.CANCELLED, msg="Cancelled by user")
            raise
        except Exception as e:
            _emit(TaskStatus.FAILED, msg=str(e))
            raise
        finally:
            # Always try to clean temp
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass

    def cancel(self) -> None:
        """Signal the current task to cancel."""
        self._cancelled = True
