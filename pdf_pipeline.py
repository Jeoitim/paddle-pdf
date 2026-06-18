"""
PDF Processing Pipeline
Handles PDF page extraction, OCR processing, and output generation.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Tuple
import tempfile

import fitz  # PyMuPDF
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    PDF processing pipeline:
    1. Extract pages as images
    2. Run OCR on each page
    3. Generate searchable PDF + text output
    """

    SUPPORTED_IMAGE_FORMATS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}

    def __init__(
        self,
        ocr_engine,
        dpi: int = 300,
        max_pages: Optional[int] = None,
        temp_dir: Optional[Path] = None,
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

    def extract_pages(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract pages from PDF as images.

        Returns:
            dict with:
                - total_pages: int
                - pages: list of (page_num, image_path) tuples
                - metadata: dict with PDF metadata
                - encrypted: bool
        """
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)

        # Get metadata
        metadata = doc.metadata or {}
        is_encrypted = doc.is_encrypted

        pages = []
        for page_num in range(1, total_pages + 1):
            if self.max_pages and page_num > self.max_pages:
                break

            page_idx = page_num - 1
            page = doc[page_idx]

            # Render page to image
            zoom = self.dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Save as PNG
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
        pages: List[Tuple[int, str]],
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Run OCR on extracted pages.

        Args:
            pages: list of (page_num, image_path) tuples
            progress_callback: optional callback(page_num, lines, elapsed) for progress updates

        Returns:
            dict with OCR results per page and statistics
        """
        results = []
        total_lines = 0
        total_conf_sum = 0.0  # sum of all individual line confidences (percentage)
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
                # conf is page avg (percentage). Reconstruct sum of all line confs
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

        # Compute overall statistics
        pages_with_text = sum(1 for r in results if r["num_lines"] > 0)
        avg_conf = (total_conf_sum / total_lines * 100) if total_lines > 0 else 0.0

        stats = {
            "pages_processed": len(results),
            "pages_with_text": pages_with_text,
            "total_lines": total_lines,
            "avg_confidence": avg_conf,
            "total_elapsed": total_elapsed,
            "failed_pages": failed_pages,
        }

        return {
            "pages": results,
            "stats": stats,
        }

    def save_output(
        self,
        ocr_result: Dict[str, Any],
        input_pdf: Path,
        output_dir: Path,
        show_conf: bool = False,
    ) -> Dict[str, Path]:
        """
        Generate output files:
        - Searchable PDF (with text layer)
        - Plain text file

        Args:
            show_conf: if True, include confidence scores in text output
        """
        pdf_output = output_dir / f"{input_pdf.stem}_可搜索.pdf"
        txt_output = output_dir / f"{input_pdf.stem}_文字.txt"

        # --- Generate searchable PDF ---
        self._generate_searchable_pdf(
            ocr_result=ocr_result,
            input_pdf=input_pdf,
            output_path=pdf_output,
        )

        # --- Generate plain text ---
        self._generate_text_output(
            ocr_result=ocr_result,
            output_path=txt_output,
            show_conf=show_conf,
        )

        return {
            "pdf": pdf_output,
            "txt": txt_output,
        }

    def _generate_searchable_pdf(
        self,
        ocr_result: Dict[str, Any],
        input_pdf: Path,
        output_path: Path,
    ) -> None:
        """Create a searchable PDF with text overlay."""
        # Open source PDF
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

            # Get page dimensions
            page_width = page.rect.width
            page_height = page.rect.height

            # Get image dimensions from the extracted page
            img_path = result.get("image_path")
            if img_path and os.path.exists(img_path):
                with Image.open(img_path) as img:
                    img_w, img_h = img.size
            else:
                img_w, img_h = page_width, page_height

            scale_x = page_width / img_w
            scale_y = page_height / img_h

            # Font configuration (Windows/macOS/Linux system Chinese fonts)
            font_path = None
            possible_fonts = [
                # Windows
                r"C:\Windows\Fonts\simsun.ttc",  # 宋体
                r"C:\Windows\Fonts\msyh.ttc",  # 微软雅黑
                r"C:\Windows\Fonts\simhei.ttc",  # 黑体
                # macOS
                "/System/Library/Fonts/PingFang.ttc",
                "/Library/Fonts/Arial Unicode.ttf",
                # Linux (Ubuntu/Debian)
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            ]
            for p in possible_fonts:
                if os.path.exists(p):
                    font_path = p
                    break

            # Initialize Font for width measurement and pre-register on page
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

                # Get bounding box directly from line_data
                bbox = line_data.get("bbox")
                if bbox is None:
                    continue

                # bbox can be 4-point polygon [[x,y], [x,y], [x,y], [x,y]] or 4-tuple (x0,y0,x1,y1)
                if isinstance(bbox, (list, np.ndarray)):
                    if len(bbox) == 4 and len(bbox[0]) == 2:
                        # 4-point polygon: get min/max for axis-aligned bbox
                        pts = np.array(bbox)
                        x0, y0 = pts.min(axis=0)
                        x1, y1 = pts.max(axis=0)
                    else:
                        x0, y0, x1, y1 = bbox
                else:
                    x0, y0, x1, y1 = bbox

                # Scale coordinates to PDF points
                rx0 = x0 * scale_x
                ry0 = y0 * scale_y
                rx1 = x1 * scale_x
                ry1 = y1 * scale_y

                target_width = rx1 - rx0
                target_height = ry1 - ry0

                if target_width <= 0 or target_height <= 0:
                    continue

                # Calculate font size by matching width and height
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

                # Calculate baseline point, centering the font cell vertically
                baseline_y = ry0 + (target_height - fontsize) / 2 + ascender * fontsize
                point = fitz.Point(rx0, baseline_y)

                # Insert text in invisible mode (render_mode=3) using embedded/registered font
                try:
                    page.insert_text(
                        point,
                        text,
                        fontsize=fontsize,
                        fontname=font_name,
                        render_mode=3,  # 3 = invisible text (not filled, not stroked)
                    )
                except Exception:
                    # Fallback: try visible text without custom font/render_mode
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
        print(f"      Searchable PDF saved: {output_path.name}")

    def _generate_text_output(
        self,
        ocr_result: Dict[str, Any],
        output_path: Path,
        show_conf: bool = False,
    ) -> None:
        """Generate plain text file from OCR results.

        Args:
            show_conf: if True, include confidence scores after each line
        """
        lines_out = []

        lines_out.append(f"OCR Result - Generated by pdf2txt")
        lines_out.append(f"Model: {self.ocr.model_name}")
        lines_out.append(f"GPU: {'Yes' if self.ocr.use_gpu else 'No'}")
        lines_out.append("=" * 60)
        lines_out.append("")

        stats = ocr_result.get("stats", {})

        for page_result in ocr_result["pages"]:
            page_num = page_result["page_num"]
            lines = page_result.get("lines", [])
            conf = page_result.get("avg_confidence", 0)

            lines_out.append(
                f"--- Page {page_num} ({page_result['num_lines']} lines, conf={conf:.1f}%) ---"
            )

            for line_data in lines:
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

        text = "\n".join(lines_out)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"      Text file saved: {output_path.name}")


# --- PDF page extraction using pdf2image (alternative) ---
def extract_pages_pdf2image(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = 300,
    max_pages: Optional[int] = None,
) -> List[Tuple[int, str]]:
    """
    Extract PDF pages using pdf2image (poppler-based).

    Returns list of (page_num, image_path) tuples.
    """
    from pdf2image import convert_from_path

    poppler_path = None
    # Try to find poppler
    possible_paths = [
        r"C:\Program Files\poppler\Library\bin",
        r"C:\poppler\Library\bin",
    ]
    for p in possible_paths:
        if os.path.exists(p):
            poppler_path = p
            break

    images = convert_from_path(
        str(pdf_path),
        dpi=dpi,
        first_page=1,
        last_page=max_pages,
        poppler_path=poppler_path,
    )

    pages = []
    for i, img in enumerate(images):
        page_num = i + 1
        img_path = output_dir / f"page_{page_num:04d}.png"
        img.save(str(img_path), "PNG")
        pages.append((page_num, str(img_path)))

    return pages
