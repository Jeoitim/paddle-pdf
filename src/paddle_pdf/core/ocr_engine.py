"""PaddleOCR engine wrapper with GPU/CPU support."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from .gpu_utils import configure_cuda_for_engine

logger = logging.getLogger(__name__)


class PaddleOCREngine:
    """PaddleOCR wrapper with lazy initialization and GPU/CPU support."""

    MODEL_CONFIG: dict[str, dict[str, Any]] = {
        "ch": {
            "det_model": "ch_PP-OCRv4/ch_PP-OCRv4_det_infer.tar",
            "rec_model": "ch_PP-OCRv4/ch_PP-OCRv4_rec_infer.tar",
            "cls_model": "ch_ppocr_mobile_v2.0/cls_infer.tar",
            "rec_char_dict": "ppocr/utils/ppocr_keys_v1.txt",
            "lang": "ch",
            "det_limit_side_len": 960,
            "det_limit_type": "max",
        },
        "ch_plus": {
            "det_model": "ch_PP-OCRv4/ch_PP-OCRv4_det_infer.tar",
            "rec_model": "ch_PP-OCRv4/ch_PP-OCRv4_rec_slim_infer.tar",
            "cls_model": "ch_ppocr_mobile_v2.0/cls_infer.tar",
            "rec_char_dict": "ppocr/utils/ppocr_keys_v1.txt",
            "lang": "ch",
            "det_limit_side_len": 960,
            "det_limit_type": "max",
        },
        "ch_server_v2": {
            "det_model": "ch_PP-OCRv4_server/det/inference.tar",
            "rec_model": "ch_PP-OCRv4_server/rec/inference.tar",
            "cls_model": "ch_ppocr_mobile_v2.0/cls_infer.tar",
            "rec_char_dict": "ppocr/utils/ppocr_keys_v1.txt",
            "lang": "ch",
            "det_limit_side_len": 1920,
            "det_limit_type": "max",
        },
        "en": {
            "det_model": "en_PP-OCRv4/en_PP-OCRv4_det_infer.tar",
            "rec_model": "en_PP-OCRv4/en_PP-OCRv4_rec_infer.tar",
            "cls_model": "ch_ppocr_mobile_v2.0/cls_infer.tar",
            "rec_char_dict": "ppocr/utils/en_dict.txt",
            "lang": "en",
            "det_limit_side_len": 960,
            "det_limit_type": "max",
        },
        "cyrillic": {
            "det_model": "ru_PP-OCRv4/ru_PP-OCRv4_det_infer.tar",
            "rec_model": "ru_PP-OCRv4/ru_PP-OCRv4_rec_infer.tar",
            "cls_model": "ch_ppocr_mobile_v2.0/cls_infer.tar",
            "rec_char_dict": "ppocr/utils/russian_dict.txt",
            "lang": "ru",
            "det_limit_side_len": 960,
            "det_limit_type": "max",
        },
        "japanese": {
            "det_model": "japan_PP-OCRv4/japan_PP-OCRv4_det_infer.tar",
            "rec_model": "japan_PP-OCRv4/japan_PP-OCRv4_rec_infer.tar",
            "cls_model": "ch_ppocr_mobile_v2.0/cls_infer.tar",
            "rec_char_dict": "ppocr/utils/japan_dict.txt",
            "lang": "japan",
            "det_limit_side_len": 960,
            "det_limit_type": "max",
        },
        "korean": {
            "det_model": "korean_PP-OCRv4/korean_PP-OCRv4_det_infer.tar",
            "rec_model": "korean_PP-OCRv4/korean_PP-OCRv4_rec_infer.tar",
            "cls_model": "ch_ppocr_mobile_v2.0/cls_infer.tar",
            "rec_char_dict": "ppocr/utils/korean_dict.txt",
            "lang": "korean",
            "det_limit_side_len": 960,
            "det_limit_type": "max",
        },
    }

    def __init__(
        self,
        use_gpu: bool = False,
        model_name: str = "ch",
        use_angle_cls: bool = True,
        det_limit_side_len: int | None = None,
        verbose: bool = False,
    ):
        self.use_gpu = use_gpu
        self.model_name = model_name
        self.use_angle_cls = use_angle_cls
        self.det_limit_side_len = det_limit_side_len
        self.verbose = verbose
        self._ocr = None
        self._initialized = False

        if self.use_gpu:
            configure_cuda_for_engine(verbose=self.verbose)

    def _get_model_dir(self, model_name: str) -> Path:
        return Path.home() / ".paddleocr" / "ocr" / model_name

    def is_model_available(self, model_name: str) -> bool:
        """Check if model is cached locally."""
        model_dir = self._get_model_dir(model_name)
        if model_dir.exists():
            if any(model_dir.rglob("*.inference")) or any(
                model_dir.rglob("inference.*")
            ):
                return True
            if any(model_dir.rglob("model")):
                return True
        try:
            from paddleocr import get_model_config

            configs = get_model_config()
            for cfg in configs:
                if cfg.get("name") == model_name:
                    return True
        except Exception:
            pass
        return False

    def check_gpu(self) -> bool:
        """Check if GPU is available and working."""
        try:
            import paddle

            if paddle.device.cuda.device_count() > 0:
                paddle.device.set_device("gpu:0")
                x = paddle.to_tensor([1.0])
                _ = x * 2
                return True
        except Exception as e:
            if self.verbose:
                logger.warning(f"GPU check failed: {e}")
        return False

    def initialize(self) -> PaddleOCREngine:
        if self._initialized:
            return self

        # Resolve permission issues on paddlex directories dynamically
        from paddle_pdf.core.models import check_and_apply_fallback
        check_and_apply_fallback(self.model_name)

        from paddleocr import PaddleOCR
        import paddle

        config = self.MODEL_CONFIG.get(self.model_name, self.MODEL_CONFIG["ch"])

        if self.use_gpu:
            try:
                paddle.device.set_device("gpu:0")
                if self.verbose:
                    logger.info("Device set to GPU (gpu:0)")
            except Exception as e:
                if self.verbose:
                    logger.warning(
                        f"GPU mode requested but failed: {e}. Falling back to CPU."
                    )
                self.use_gpu = False
                paddle.device.set_device("cpu")
        else:
            paddle.device.set_device("cpu")

        # Determine det_limit_side_len:
        # If specified by user, use it.
        # Otherwise, GPU mode defaults to 4320 to maximize quality (supports up to 500 DPI for typical pages),
        # while CPU mode defaults to 1920 (balancing quality and CPU memory/time).
        if self.det_limit_side_len is not None:
            limit_side_len = self.det_limit_side_len
        else:
            limit_side_len = 4320 if self.use_gpu else 1920

        ocr_kwargs: dict[str, Any] = {
            "use_textline_orientation": self.use_angle_cls,
            "lang": config["lang"],
            "text_det_limit_side_len": limit_side_len,
            "text_det_limit_type": config.get("det_limit_type", "max"),
        }

        if self.verbose:
            logger.info(f"Initializing PaddleOCR (GPU={self.use_gpu})")

        # Check if PaddleOCR is 3.x (Paddlex backend)
        import inspect
        sig = inspect.signature(PaddleOCR.__init__)
        is_paddlex_backend = "text_detection_model_name" in sig.parameters

        if is_paddlex_backend:
            # Map name to paddlex model names
            paddlex_mapping = {
                "ch": ("PP-OCRv4_mobile_det", "PP-OCRv4_mobile_rec"),
                "ch_plus": ("PP-OCRv4_mobile_det", "PP-OCRv4_mobile_rec"),
                "ch_server_v2": ("PP-OCRv5_server_det", "PP-OCRv5_server_rec"),
                "en": ("PP-OCRv4_mobile_det", "en_PP-OCRv5_mobile_rec"),
            }
            if self.model_name in paddlex_mapping:
                ocr_kwargs["text_detection_model_name"] = paddlex_mapping[self.model_name][0]
                ocr_kwargs["text_recognition_model_name"] = paddlex_mapping[self.model_name][1]
            
            # Disable unwarping and orientation classification to keep original scanned coordinates intact
            ocr_kwargs["use_doc_unwarping"] = False
            ocr_kwargs["use_doc_orientation_classify"] = False
            
            if self.verbose:
                logger.info(f"  Paddlex backend detected")
                logger.info(f"  text_detection_model_name: {ocr_kwargs.get('text_detection_model_name', 'default')}")
                logger.info(f"  text_recognition_model_name: {ocr_kwargs.get('text_recognition_model_name', 'default')}")
        else:
            model_dir = self._get_model_dir(self.model_name)
            if self.is_model_available(self.model_name):
                ocr_kwargs["det_model_dir"] = str(model_dir / "det")
                ocr_kwargs["rec_model_dir"] = str(model_dir / "rec")
                ocr_kwargs["cls_model_dir"] = str(model_dir / "cls")
            
            if self.verbose:
                logger.info(f"  Legacy backend detected")
                logger.info(f"  det_model_dir: {ocr_kwargs.get('det_model_dir', 'default')}")

        self._ocr = PaddleOCR(**ocr_kwargs)
        self._initialized = True
        return self

    def recognize(self, image_path: str) -> dict[str, Any]:
        """Run OCR on a single image. Returns structured result."""
        if not self._initialized:
            self.initialize()

        t0 = time.time()
        raw_result = self._ocr.ocr(image_path)
        elapsed = time.time() - t0

        lines: list[dict[str, Any]] = []
        total_conf = 0.0

        if raw_result and len(raw_result) > 0:
            ocr_result = raw_result[0]
            try:
                rec_texts = ocr_result["rec_texts"]
                rec_scores = ocr_result["rec_scores"]
                rec_polys = ocr_result.get("rec_polys", ocr_result.get("rec_boxes", []))
            except (KeyError, TypeError):
                # Fallback: old format [[bbox, (text, score), ...]]
                try:
                    rec_texts = []
                    rec_scores = []
                    rec_polys = []
                    for item in ocr_result:
                        if len(item) >= 2:
                            text_info = item[1]
                            if isinstance(text_info, (list, tuple)):
                                text = text_info[0]
                                score = text_info[1] if len(text_info) > 1 else 1.0
                            else:
                                text = text_info
                                score = 1.0
                            rec_texts.append(text)
                            rec_scores.append(score)
                            rec_polys.append(item[0])
                except (TypeError, KeyError):
                    rec_texts, rec_scores, rec_polys = [], [], []

            if len(rec_polys) < len(rec_texts):
                rec_polys = list(rec_polys) + [None] * (
                    len(rec_texts) - len(rec_polys)
                )

            for text, score, poly in zip(rec_texts, rec_scores, rec_polys):
                lines.append({"text": text, "confidence": float(score), "bbox": poly})
                total_conf += float(score)

        num_lines = len(lines)
        avg_conf = (total_conf / num_lines * 100) if num_lines > 0 else 0.0

        return {
            "lines": lines,
            "full_result": raw_result,
            "num_lines": num_lines,
            "avg_confidence": avg_conf,
            "elapsed": elapsed,
            "image_path": image_path,
        }

    def recognize_batch(self, image_paths: list[str]) -> list[dict[str, Any]]:
        """Run OCR on multiple images."""
        return [self.recognize(p) for p in image_paths]
