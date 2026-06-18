"""
PaddleOCR Engine - GPU/CPU support with model management

GPU Setup:
  1. Install CUDA Toolkit (if not present): https://developer.nvidia.com/cuda-downloads
     - PaddlePaddle supports CUDA 11.x and 12.x
     - CUDA 13.x is detected but PaddlePaddle wheels may not be available yet
  2. Run: pixi install
  3. Use: pixi run run-gpu -- -i "book.pdf"
"""

import os
import sys
import time
import logging
import glob
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


def _detect_cuda_environment() -> Dict[str, Optional[str]]:
    """
    Auto-detect CUDA Toolkit installation and return environment settings.
    This is used by the GPU mode to configure the correct DLL paths.
    """
    result = {
        "cuda_root": None,
        "cuda_version": None,
        "runtime_path": None,
        "runtime_dlls": None,
    }

    # Standard CUDA installation path
    cuda_base = Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA")
    if not cuda_base.exists():
        return result

    # Find the newest CUDA version
    cuda_versions = []
    for d in cuda_base.iterdir():
        if d.is_dir() and d.name.lower().startswith("v"):
            nvcc = d / "bin" / "nvcc.exe"
            if nvcc.exists():
                cuda_versions.append(d.name)

    if not cuda_versions:
        return result

    # Sort by version number
    def ver_key(v):
        return tuple(int(x) for x in v[1:].split("."))

    cuda_versions.sort(key=ver_key, reverse=True)
    newest = cuda_versions[0]
    cuda_root = str(cuda_base / newest)
    result["cuda_root"] = cuda_root
    result["cuda_version"] = newest

    # Find CUDA runtime DLL path
    runtime_candidates = [
        os.path.join(cuda_root, "bin", "x64"),  # CUDA 13.x style
        os.path.join(cuda_root, "bin"),  # CUDA 11.x/12.x style
    ]

    # Also check conda pkgs for CUDA runtime
    conda_base = os.path.dirname(
        cuda_root.split("\\CUDA\\")[0] if "\\CUDA\\" in cuda_root else cuda_root
    )
    conda_pkgs = os.path.join(conda_base, "pkgs")
    if os.path.exists(conda_pkgs):
        for d in os.listdir(conda_pkgs):
            if "cuda-cudart" in d.lower() and "dev" not in d.lower():
                p = os.path.join(conda_pkgs, d, "Library", "bin")
                if os.path.exists(p):
                    runtime_candidates.append(p)

    for p in runtime_candidates:
        if os.path.exists(p):
            dlls = os.listdir(p)
            if any("cudart" in f.lower() for f in dlls):
                result["runtime_path"] = p
                result["runtime_dlls"] = [f for f in dlls if "cudart" in f.lower()]
                break

    return result


def _setup_gpu_environment() -> bool:
    """
    Set up CUDA environment for PaddlePaddle GPU.
    This modifies os.environ to include CUDA DLLs in PATH.
    Returns True if CUDA environment was configured.
    """
    cuda_info = _detect_cuda_environment()

    if not cuda_info["cuda_root"]:
        logger.warning("CUDA Toolkit not found. GPU mode will not be available.")
        return False

    logger.info(
        f"CUDA detected: {cuda_info['cuda_version']} at {cuda_info['cuda_root']}"
    )

    if cuda_info["runtime_path"]:
        logger.info(f"CUDA runtime DLLs: {cuda_info['runtime_path']}")
        current_path = os.environ.get("PATH", "")
        if cuda_info["runtime_path"] not in current_path:
            os.environ["PATH"] = cuda_info["runtime_path"] + os.pathsep + current_path
        os.environ["CUDA_HOME"] = cuda_info["cuda_root"]
        os.environ["CUDA_PATH"] = cuda_info["cuda_root"]
        return True

    return False


class PaddleOCREngine:
    """
    PaddleOCR wrapper with GPU/CPU support and model management.

    Supported models:
        ch              - Chinese + English (mobile slim, fastest)
        ch_plus         - Chinese + English (server, more accurate)
        ch_server_v2    - Chinese + English (latest server version)
        en              - English
        cyrillic        - Cyrillic
        japanese        - Japanese + Chinese
        korean          - Korean + Chinese
    """

    # Model configuration
    MODEL_CONFIG: Dict[str, Dict[str, Any]] = {
        # Chinese models
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
        # English model
        "en": {
            "det_model": "en_PP-OCRv4/en_PP-OCRv4_det_infer.tar",
            "rec_model": "en_PP-OCRv4/en_PP-OCRv4_rec_infer.tar",
            "cls_model": "ch_ppocr_mobile_v2.0/cls_infer.tar",
            "rec_char_dict": "ppocr/utils/en_dict.txt",
            "lang": "en",
            "det_limit_side_len": 960,
            "det_limit_type": "max",
        },
        # Cyrillic
        "cyrillic": {
            "det_model": "ru_PP-OCRv4/ru_PP-OCRv4_det_infer.tar",
            "rec_model": "ru_PP-OCRv4/ru_PP-OCRv4_rec_infer.tar",
            "cls_model": "ch_ppocr_mobile_v2.0/cls_infer.tar",
            "rec_char_dict": "ppocr/utils/russian_dict.txt",
            "lang": "ru",
            "det_limit_side_len": 960,
            "det_limit_type": "max",
        },
        # Japanese
        "japanese": {
            "det_model": "japan_PP-OCRv4/japan_PP-OCRv4_det_infer.tar",
            "rec_model": "japan_PP-OCRv4/japan_PP-OCRv4_rec_infer.tar",
            "cls_model": "ch_ppocr_mobile_v2.0/cls_infer.tar",
            "rec_char_dict": "ppocr/utils/japan_dict.txt",
            "lang": "japan",
            "det_limit_side_len": 960,
            "det_limit_type": "max",
        },
        # Korean
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
        verbose: bool = False,
    ):
        self.use_gpu = use_gpu
        self.model_name = model_name
        self.use_angle_cls = use_angle_cls
        self.verbose = verbose
        self._ocr = None
        self._initialized = False

        # Auto-configure CUDA environment if GPU mode requested
        if self.use_gpu:
            cuda_info = _detect_cuda_environment()
            if cuda_info["cuda_root"]:
                if cuda_info["runtime_path"]:
                    current_path = os.environ.get("PATH", "")
                    if cuda_info["runtime_path"] not in current_path:
                        os.environ["PATH"] = (
                            cuda_info["runtime_path"] + os.pathsep + current_path
                        )
                    os.environ["CUDA_HOME"] = cuda_info["cuda_root"]
                    os.environ["CUDA_PATH"] = cuda_info["cuda_root"]
                    if verbose:
                        logger.info(
                            f"CUDA configured: {cuda_info['cuda_version']} ({cuda_info['cuda_root']})"
                        )
                        logger.info(f"Runtime DLLs: {cuda_info['runtime_path']}")
                else:
                    if verbose:
                        logger.warning(
                            f"CUDA {cuda_info['cuda_version']} found but runtime DLLs not detected"
                        )
            else:
                if verbose:
                    logger.warning("CUDA Toolkit not found in standard location")

    def _get_model_dir(self, model_name: str) -> Path:
        """Get model cache directory."""
        home = Path.home()
        cache_dir = home / ".paddleocr" / "ocr" / model_name
        return cache_dir

    def is_model_available(self, model_name: str) -> bool:
        """Check if model is cached locally."""
        # Try to find the inference model files
        model_dir = self._get_model_dir(model_name)
        config = self.MODEL_CONFIG.get(model_name, {})
        det_model = config.get("det_model", "")
        rec_model = config.get("rec_model", "")

        # Check if any model files exist in the directory
        if model_dir.exists():
            # If the directory has model files, it's available
            if any(model_dir.rglob("*.inference")) or any(
                model_dir.rglob("inference.*")
            ):
                return True
            # Also check for extracted tar contents
            if any(model_dir.rglob("model")):
                return True

        # Try paddleocr's default detection
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
                # Try a simple GPU operation
                paddle.device.set_device("gpu:0")
                x = paddle.to_tensor([1.0])
                _ = x * 2
                return True
        except Exception as e:
            err_msg = str(e)
            if self.verbose:
                logger.warning(f"GPU check failed: {e}")

            # Provide helpful error messages
            if "cudnn64_8" in err_msg or "cudnn" in err_msg.lower():
                logger.error(
                    "cuDNN not found. GPU requires cuDNN to be installed.\n"
                    "  1. Download cuDNN from: https://developer.nvidia.com/cudnn\n"
                    "  2. Extract to CUDA root: C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v13.2\n"
                    "  3. Add cuDNN bin to PATH, or use CPU mode.\n"
                    "  Falling back to CPU mode."
                )
            elif "PreconditionNotMet" in err_msg:
                logger.error(
                    f"GPU library error: {err_msg[:200]}\n"
                    "  Falling back to CPU mode."
                )
        return False

    def initialize(self) -> "PaddleOCREngine":
        """Initialize the OCR engine (lazy initialization)."""
        if self._initialized:
            return self

        from paddleocr import PaddleOCR
        import paddle

        config = self.MODEL_CONFIG.get(self.model_name, self.MODEL_CONFIG["ch"])

        # Set device before PaddleOCR init (PaddleOCR 3.x uses this to decide GPU/CPU)
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

        # Build PaddleOCR init arguments (PaddleOCR 3.x API)
        ocr_kwargs = {
            "use_textline_orientation": self.use_angle_cls,
            "lang": config["lang"],
            "text_det_limit_side_len": config.get("det_limit_side_len", 960),
            "text_det_limit_type": config.get("det_limit_type", "max"),
        }

        if self.verbose:
            logger.info(f"Initializing PaddleOCR (GPU={self.use_gpu})")

        # Model-specific settings
        model_dir = self._get_model_dir(self.model_name)
        if self.is_model_available(self.model_name):
            ocr_kwargs["det_model_dir"] = str(model_dir / "det")
            ocr_kwargs["rec_model_dir"] = str(model_dir / "rec")
            ocr_kwargs["cls_model_dir"] = str(model_dir / "cls")

        if self.verbose:
            logger.info(f"Initializing PaddleOCR (GPU={self.use_gpu})")
            logger.info(f"  model: {self.model_name}")
            logger.info(f"  lang: {config['lang']}")
            logger.info(
                f"  det_model_dir: {ocr_kwargs.get('det_model_dir', 'default')}"
            )

        self._ocr = PaddleOCR(**ocr_kwargs)
        self._initialized = True
        return self

    def recognize(self, image_path: str) -> Dict[str, Any]:
        """
        Run OCR on a single image.

        Returns:
            dict with keys:
                - lines: list of (text, confidence) tuples
                - full_result: raw PaddleOCR result
                - num_lines: number of text lines found
                - avg_confidence: average confidence
        """
        if not self._initialized:
            self.initialize()

        t0 = time.time()
        raw_result = self._ocr.ocr(image_path)
        elapsed = time.time() - t0

        lines = []
        total_conf = 0.0

        # PaddleOCR 3.x returns [OCRResult] where OCRResult is dict-like
        # Keys: dt_polys, rec_texts, rec_scores, rec_polys, rec_boxes
        if raw_result and len(raw_result) > 0:
            ocr_result = raw_result[0]
            # Support both new OCRResult format and old list format
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
                    rec_texts = []
                    rec_scores = []
                    rec_polys = []

            # Ensure rec_polys has the same length as rec_texts
            if len(rec_polys) < len(rec_texts):
                rec_polys = list(rec_polys) + [None] * (len(rec_texts) - len(rec_polys))

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

    def recognize_batch(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """Run OCR on multiple images."""
        return [self.recognize(p) for p in image_paths]


def download_model(model_name: str, force: bool = False) -> bool:
    """
    Download a PaddleOCR model using paddleocr's built-in downloader.

    Returns True if successful, False otherwise.
    """
    try:
        from paddleocr import PaddleOCR
        from paddleocr.download import download_with_progressbar

        # The model will be downloaded automatically by PaddleOCR on first use
        # This function provides a manual trigger with error handling
        config = PaddleOCREngine.MODEL_CONFIG.get(model_name)
        if not config:
            print(f"[ERROR] Unknown model: {model_name}")
            return False

        print(f"Attempting to download model: {model_name}")
        print(f"  Lang: {config['lang']}")

        # Try paddleocr's built-in download mechanism
        ocr = PaddleOCR(lang=config["lang"])
        print(
            f"[OK] Model '{model_name}' is ready (downloaded by PaddleOCR on first run)"
        )
        return True

    except ImportError as e:
        print(f"[ERROR] PaddleOCR not installed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        return False
