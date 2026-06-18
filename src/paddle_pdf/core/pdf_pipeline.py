"""PDF processing pipeline — extract, OCR, generate output."""

from __future__ import annotations

import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF processing pipeline: extract pages → run OCR → save output."""

    def __init__(
        self,
        ocr_engine: Any,
        dpi: int = 300,
        max_pages: int | None = None,
        temp_dir: Path | None = None,
        verbose: bool = False,
    ):
        self.ocr = ocr_engine
        self.dpi = dpi
        self.max_pages = max_pages
        self.temp_dir = (
            Path(temp_dir) if temp_dir else Path(tempfile.mkdtemp(prefix="pdf_ocr_"))
        )
        self.verbose = verbose
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def extract_pages(self, pdf_path: Path) -> dict[str, Any]:
        """Extract pages from PDF as images."""
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        metadata = doc.metadata or {}
        is_encrypted = doc.is_encrypted

        pages: list[tuple[int, str]] = []
        for page_num in range(1, total_pages + 1):
            if self.max_pages and page_num > self.max_pages:
                break

            page = doc[page_num - 1]
            zoom = self.dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            img_path = self.temp_dir / f"page_{page_num:04d}.png"
            pix.save(str(img_path))
            pages.append((page_num, str(img_path)))

            if self.verbose:
                logger.info(
                    f"  Page {page_num}/{total_pages} extracted -> {img_path.name}"
                )

        doc.close()
        return {
            "total_pages": total_pages,
            "pages": pages,
            "metadata": metadata,
            "encrypted": is_encrypted,
        }

    def run_ocr(
        self,
        pages: list[tuple[int, str]],
        progress_callback: Callable[[int, int, float], None] | None = None,
    ) -> dict[str, Any]:
        """Run OCR on extracted pages with optional progress callback."""
        results: list[dict[str, Any]] = []
        total_lines = 0
        total_conf_sum = 0.0
        total_elapsed = 0.0
        failed_pages = 0

        for page_num, img_path in pages:
            t0 = time.time()
            try:
                page_result = self.ocr.recognize(img_path)
                elapsed = page_result.get("elapsed", time.time() - t0)
                num_lines = page_result.get("num_lines", 0)
                conf = page_result.get("avg_confidence", 0)

                results.append(
                    {
                        "page_num": page_num,
                        "image_path": img_path,
                        "lines": page_result.get("lines", []),
                        "num_lines": num_lines,
                        "avg_confidence": conf,
                        "elapsed": elapsed,
                        "full_result": page_result.get("full_result"),
                    }
                )

                total_lines += num_lines
                total_conf_sum += conf * num_lines / 100.0
                total_elapsed += elapsed

                if self.verbose:
                    print(
                        f"      Page {page_num}: {num_lines} lines, {elapsed:.1f}s, conf={conf:.1f}%"
                    )

                if progress_callback:
                    progress_callback(page_num, num_lines, elapsed)

            except Exception as e:
                failed_pages += 1
                logger.error(f"OCR failed for page {page_num}: {e}")
                elapsed = time.time() - t0
                results.append(
                    {
                        "page_num": page_num,
                        "image_path": img_path,
                        "lines": [],
                        "num_lines": 0,
                        "avg_confidence": 0.0,
                        "elapsed": elapsed,
                        "error": str(e),
                    }
                )
                if progress_callback:
                    progress_callback(page_num, 0, elapsed)

        pages_with_text = sum(1 for r in results if r["num_lines"] > 0)
        avg_conf = (total_conf_sum / total_lines * 100) if total_lines > 0 else 0.0

        return {
            "pages": results,
            "stats": {
                "pages_processed": len(results),
                "pages_with_text": pages_with_text,
                "total_lines": total_lines,
                "avg_confidence": avg_conf,
                "total_elapsed": total_elapsed,
                "failed_pages": failed_pages,
            },
        }

    def save_output(
        self,
        ocr_result: dict[str, Any],
        input_pdf: Path,
        output_dir: Path,
        show_conf: bool = False,
    ) -> dict[str, Path]:
        """Generate searchable PDF and plain text file."""
        pdf_output = output_dir / f"{input_pdf.stem}_可搜索.pdf"
        txt_output = output_dir / f"{input_pdf.stem}_文字.txt"

        self._generate_searchable_pdf(
            ocr_result=ocr_result,
            input_pdf=input_pdf,
            output_path=pdf_output,
        )
        self._generate_text_output(
            ocr_result=ocr_result,
            output_path=txt_output,
            show_conf=show_conf,
        )

        return {"pdf": pdf_output, "txt": txt_output}

    def _generate_searchable_pdf(
        self,
        ocr_result: dict[str, Any],
        input_pdf: Path,
        output_path: Path,
    ) -> None:
        """Create a searchable PDF with invisible text overlay."""
        doc = fitz.open(str(input_pdf))
        results_by_page = {r["page_num"]: r for r in ocr_result["pages"]}

        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc[page_idx]

            if page_num not in results_by_page:
                continue

            result = results_by_page[page_num]
            lines = result.get("lines", [])
            if not lines:
                continue

            page_width = page.rect.width
            page_height = page.rect.height

            img_path = result.get("image_path")
            if img_path and os.path.exists(img_path):
                with Image.open(img_path) as img:
                    img_w, img_h = img.size
            else:
                img_w, img_h = page_width, page_height

            scale_x = page_width / img_w
            scale_y = page_height / img_h

            # Font discovery (cross-platform)
            font_path = None
            possible_fonts = [
                r"C:\Windows\Fonts\simsun.ttc",
                r"C:\Windows\Fonts\msyh.ttc",
                r"C:\Windows\Fonts\simhei.ttc",
                "/System/Library/Fonts/PingFang.ttc",
                "/Library/Fonts/Arial Unicode.ttf",
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            ]
            for p in possible_fonts:
                if os.path.exists(p):
                    font_path = p
                    break

            if font_path:
                try:
                    font = fitz.Font(fontname="simsun", fontfile=font_path)
                    font_name = "simsun"
                except Exception:
                    font = fitz.Font("cjk")
                    font_name = "cjk"
            else:
                font = fitz.Font("cjk")
                font_name = "cjk"

            try:
                if font_path and font_name == "simsun":
                    page.insert_font(fontname=font_name, fontfile=font_path)
                else:
                    page.insert_font(fontname=font_name, fontbuffer=font.buffer)
            except Exception:
                try:
                    font = fitz.Font("cjk")
                    font_name = "cjk"
                    page.insert_font(fontname=font_name, fontbuffer=font.buffer)
                except Exception:
                    pass

            ascender = getattr(font, "ascender", 0.8)

            for line_data in lines:
                text = line_data.get("text", "").strip()
                if not text:
                    continue

                bbox = line_data.get("bbox")
                if bbox is None:
                    continue

                if isinstance(bbox, (list, np.ndarray)):
                    if len(bbox) == 4 and len(bbox[0]) == 2:
                        pts = np.array(bbox)
                        x0, y0 = pts.min(axis=0)
                        x1, y1 = pts.max(axis=0)
                    else:
                        x0, y0, x1, y1 = bbox
                else:
                    x0, y0, x1, y1 = bbox

                rx0 = x0 * scale_x
                ry0 = y0 * scale_y
                rx1 = x1 * scale_x
                ry1 = y1 * scale_y

                target_width = rx1 - rx0
                target_height = ry1 - ry0
                if target_width <= 0 or target_height <= 0:
                    continue

                ref_fs = 10.0
                try:
                    measured_width = font.text_length(text, fontsize=ref_fs)
                except Exception:
                    measured_width = 0.0

                if measured_width > 0:
                    fs_by_width = ref_fs * target_width / measured_width
                else:
                    fs_by_width = target_height

                fs_by_height = target_height * 0.95
                fontsize = max(min(fs_by_width, fs_by_height), 1.0)

                baseline_y = ry0 + (target_height - fontsize) / 2 + ascender * fontsize
                point = fitz.Point(rx0, baseline_y)

                try:
                    page.insert_text(
                        point,
                        text,
                        fontsize=fontsize,
                        fontname=font_name,
                        render_mode=3,
                    )
                except Exception:
                    try:
                        page.insert_text(
                            point,
                            text,
                            fontsize=fontsize,
                            color=(0.95, 0.95, 0.95),
                        )
                    except Exception:
                        pass

        doc.save(str(output_path), garbage=4, deflate=True)
        doc.close()
        logger.info(f"Searchable PDF saved: {output_path.name}")

    def _generate_text_output(
        self,
        ocr_result: dict[str, Any],
        output_path: Path,
        show_conf: bool = False,
    ) -> None:
        """Generate plain text file from OCR results."""
        lines_out: list[str] = []

        lines_out.append("OCR Result - Generated by PaddlePDF")
        lines_out.append(f"Model: {self.ocr.model_name}")
        lines_out.append(f"GPU: {'Yes' if self.ocr.use_gpu else 'No'}")
        lines_out.append("=" * 60)
        lines_out.append("")

        stats = ocr_result.get("stats", {})

        for page_result in ocr_result["pages"]:
            page_num = page_result["page_num"]
            page_lines = page_result.get("lines", [])
            conf = page_result.get("avg_confidence", 0)

            lines_out.append(
                f"--- Page {page_num} ({page_result['num_lines']} lines, conf={conf:.1f}%) ---"
            )

            for line_data in page_lines:
                text = line_data.get("text", "").strip()
                if text:
                    if show_conf:
                        score = line_data.get("confidence", 1.0)
                        lines_out.append(f"  {text}  [conf:{score:.0%}]")
                    else:
                        lines_out.append(f"  {text}")

            lines_out.append("")

        lines_out.append("=" * 60)
        lines_out.append(f"Total lines: {stats.get('total_lines', 0)}")
        lines_out.append(f"Avg confidence: {stats.get('avg_confidence', 0):.1f}%")
        lines_out.append(f"Pages processed: {stats.get('pages_processed', 0)}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines_out))

        logger.info(f"Text file saved: {output_path.name}")
