"""Model registry and management for PaddleOCR."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Legacy cache location
LEGACY_CACHE_ROOT = Path.home() / ".paddleocr" / "ocr"

# PaddleOCR 3.x / paddlex cache location helpers
def get_paddlex_cache_root() -> Path:
    """Get the active paddlex cache root directory.
    
    Checks PADDLE_PDX_CACHE_HOME or PADDLEX_HOME environment variable first, falling back to ~/.paddlex.
    """
    paddlex_home = os.environ.get("PADDLE_PDX_CACHE_HOME") or os.environ.get("PADDLEX_HOME")
    if paddlex_home:
        return Path(paddlex_home) / "official_models"
    return Path.home() / ".paddlex" / "official_models"


def setup_paddlex_fallback() -> None:
    """Redirect PaddleX and PaddleHub cache directories to fallback locations."""
    fallback_paddlex = Path.home() / ".paddlex_fallback"
    fallback_hub = Path.home() / ".paddle_hub_fallback"
    
    os.environ["PADDLEX_HOME"] = str(fallback_paddlex)
    os.environ["PADDLE_PDX_CACHE_HOME"] = str(fallback_paddlex)
    os.environ["PADDLE_HUB_HOME"] = str(fallback_hub)
    
    logger.warning(
        f"Redirecting PaddleX cache to: {fallback_paddlex} and PaddleHub cache to: {fallback_hub}"
    )


def check_and_apply_fallback(name: str) -> None:
    """Check if the default paddlex cache directories for the given model have permission issues.
    
    If a permission issue is detected, redirects to fallback cache locations.
    """
    # If the environment variable was already explicitly set (or fallback already active), do nothing
    if "PADDLE_PDX_CACHE_HOME" in os.environ or "PADDLEX_HOME" in os.environ:
        return

    paddlex_root = Path.home() / ".paddlex" / "official_models"
    if not paddlex_root.exists():
        return

    # Check the general root directory readability
    try:
        list(paddlex_root.iterdir())
    except PermissionError:
        logger.warning(
            f"Permission denied accessing PaddleX official models directory: {paddlex_root}. "
            "Enabling fallback directory..."
        )
        setup_paddlex_fallback()
        return

    # Check specific model expected subdirectories
    expected_dirs = _PADDLEX_DIRS.get(name, [])
    for d in expected_dirs:
        if not d:
            continue
        path = paddlex_root / d
        if path.exists():
            try:
                # Try listing/accessing the directory to verify read permission
                list(path.iterdir())
            except PermissionError:
                logger.warning(
                    f"Permission denied accessing PaddleX model subdirectory: {path}. "
                    "Enabling fallback directory..."
                )
                setup_paddlex_fallback()
                return

MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "ch": {
        "name": "ch (Chinese + English)",
        "desc": "Chinese, English (mobile slim, fastest, recommended for most PDFs)",
        "lang": "ch",
        "paddle_lang": "ch",
        "model_type": "PP-OCRv4 mobile",
        "note": "Smallest model, good for most use cases",
    },
    "ch_plus": {
        "name": "ch_plus (Chinese + English Plus)",
        "desc": "Chinese, English (server, more accurate than mobile)",
        "lang": "ch",
        "paddle_lang": "ch",
        "model_type": "PP-OCRv4 slim server",
        "note": "Better accuracy, larger model",
    },
    "ch_server_v2": {
        "name": "ch_server_v2 (Chinese Server v2)",
        "desc": "Chinese, English (latest server, best accuracy for complex layouts)",
        "lang": "ch",
        "paddle_lang": "ch",
        "model_type": "PP-OCRv4 server v2",
        "note": "Highest accuracy, largest model, slowest",
    },
    "en": {
        "name": "en (English)",
        "desc": "English only (optimized for English text)",
        "lang": "en",
        "paddle_lang": "en",
        "model_type": "PP-OCRv4 English",
        "note": "Best for English-only documents",
    },
    "cyrillic": {
        "name": "cyrillic",
        "desc": "Cyrillic (Russian, Ukrainian, etc.)",
        "lang": "ru",
        "paddle_lang": "ru",
        "model_type": "PP-OCRv4 Russian",
        "note": "For Cyrillic alphabet languages",
    },
    "japanese": {
        "name": "japanese",
        "desc": "Japanese, Chinese",
        "lang": "japan",
        "paddle_lang": "japan",
        "model_type": "PP-OCRv4 Japanese",
        "note": "For Japanese documents",
    },
    "korean": {
        "name": "korean",
        "desc": "Korean, Chinese",
        "lang": "korean",
        "paddle_lang": "korean",
        "model_type": "PP-OCRv4 Korean",
        "note": "For Korean documents",
    },
}

# Mapping from registry model names to paddlex directory names.
# PaddleOCR 3.x stores models under ~/.paddlex/official_models/.
# Each model requires a detection (det) and recognition (rec) model.
# Shared models (det, cls, doc_ori, textline_ori) are listed separately.
_PADDLEX_DIRS: dict[str, list[str]] = {
    "ch": [
        "PP-OCRv4_mobile_det",
        "PP-OCRv4_mobile_rec",
    ],
    "ch_plus": [
        "PP-OCRv4_mobile_det",
        "PP-OCRv4_mobile_rec",
    ],
    "ch_server_v2": [
        "PP-OCRv5_server_det",
        "PP-OCRv5_server_rec",
    ],
    "en": [
        "PP-OCRv4_mobile_det",  # uses same det model
        "en_PP-OCRv5_mobile_rec",
    ],
    "cyrillic": [
        "PP-OCRv4_mobile_det",
        # rec model name may vary; fallback to checking any ru_PP-OCRv4 dir
    ],
    "japanese": [
        "PP-OCRv4_mobile_det",
        # rec model for japanese
    ],
    "korean": [
        "PP-OCRv4_mobile_det",
        # rec model for korean
    ],
}

# Shared auxiliary models that PaddleOCR downloads for all configs
_SHARED_MODELS = [
    "PP-LCNet_x1_0_doc_ori",
    "PP-LCNet_x1_0_textline_ori",
    "UVDoc",
]


def get_model_info(name: str) -> dict[str, Any]:
    """Get information about a model by name."""
    return MODEL_REGISTRY.get(name, MODEL_REGISTRY["ch"]).copy()


def list_models() -> list[dict[str, str]]:
    """List all available models."""
    return [
        {
            "name": name,
            "desc": info["desc"],
            "lang": info["lang"],
            "note": info.get("note", ""),
        }
        for name, info in MODEL_REGISTRY.items()
    ]


def get_model_dir(name: str) -> Path:
    """Get the legacy model cache directory."""
    return LEGACY_CACHE_ROOT / name


def _dir_has_files(path: Path) -> bool:
    """Check if a directory exists and contains at least one entry.

    Catches PermissionError (Windows ACL issues with paddlex cache dirs).
    """
    try:
        return path.exists() and any(path.iterdir())
    except PermissionError:
        logger.warning("Permission denied accessing %s — treating as not cached", path)
        return False
    except OSError:
        return False


def is_model_cached(name: str) -> bool:
    """Check if model is cached locally.

    Checks both:
    1. Legacy location: ~/.paddleocr/ocr/<name>/
    2. PaddleOCR 3.x / paddlex location: ~/.paddlex/official_models/
    """
    if name not in MODEL_REGISTRY:
        return False

    # Check for permissions issue and apply fallback if needed
    check_and_apply_fallback(name)

    # Check legacy location
    legacy_dir = LEGACY_CACHE_ROOT / name
    if legacy_dir.exists():
        try:
            for f in legacy_dir.rglob("*"):
                if any(m in f.name for m in ("inference", ".tar", "model")):
                    return True
        except PermissionError:
            logger.warning("Permission denied scanning legacy cache: %s", legacy_dir)

    # Check paddlex location (PaddleOCR 3.x)
    paddlex_cache_root = get_paddlex_cache_root()
    if paddlex_cache_root.exists():
        # Check model-specific directories
        expected_dirs = _PADDLEX_DIRS.get(name, [])
        if expected_dirs:
            all_present = all(
                _dir_has_files(paddlex_cache_root / d)
                for d in expected_dirs
                if d  # skip empty strings
            )
            if all_present:
                return True

        # Fallback: scan for directories matching the model's language prefix
        lang = MODEL_REGISTRY[name].get("paddle_lang", "")
        if lang:
            prefix_map = {
                "ch": "PP-OCRv",
                "en": "en_PP-OCRv",
                "ru": "ru_PP-OCRv",
                "japan": "japan_PP-OCRv",
                "korean": "korean_PP-OCRv",
            }
            prefix = prefix_map.get(lang, "")
            if prefix:
                try:
                    for d in paddlex_cache_root.iterdir():
                        if d.is_dir() and d.name.startswith(prefix):
                            if _dir_has_files(d):
                                return True
                except PermissionError:
                    logger.warning("Permission denied scanning paddlex cache: %s", paddlex_cache_root)

    return False


def download_model(name: str, force: bool = False) -> bool:
    """Download/verify a PaddleOCR model."""
    if name not in MODEL_REGISTRY:
        logger.error(f"Unknown model: '{name}'")
        return False

    check_and_apply_fallback(name)

    info = get_model_info(name)
    logger.info(f"Model: {name} - {info['desc']}")

    if is_model_cached(name) and not force:
        logger.info(f"Model '{name}' is already cached")
        return True

    logger.info(f"Downloading model '{name}'...")

    try:
        from paddleocr import PaddleOCR
        import warnings
        import inspect

        warnings.filterwarnings("ignore")
        sig = inspect.signature(PaddleOCR.__init__)
        is_paddlex_backend = "text_detection_model_name" in sig.parameters

        if is_paddlex_backend:
            paddlex_mapping = {
                "ch": ("PP-OCRv4_mobile_det", "PP-OCRv4_mobile_rec"),
                "ch_plus": ("PP-OCRv4_mobile_det", "PP-OCRv4_mobile_rec"),
                "ch_server_v2": ("PP-OCRv5_server_det", "PP-OCRv5_server_rec"),
                "en": ("PP-OCRv4_mobile_det", "en_PP-OCRv5_mobile_rec"),
            }
            if name in paddlex_mapping:
                ocr = PaddleOCR(
                    text_detection_model_name=paddlex_mapping[name][0],
                    text_recognition_model_name=paddlex_mapping[name][1],
                    use_doc_unwarping=False,
                    use_doc_orientation_classify=False
                )
            else:
                ocr = PaddleOCR(
                    lang=info["paddle_lang"],
                    use_doc_unwarping=False,
                    use_doc_orientation_classify=False
                )
        else:
            ocr = PaddleOCR(lang=info["paddle_lang"])

        from PIL import Image
        import tempfile

        test_img = Image.new("RGB", (100, 100), color="white")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            test_path = f.name
            test_img.save(test_path)

        try:
            _ = ocr.ocr(test_path)
            logger.info(f"Model '{name}' is ready!")
            return True
        finally:
            os.unlink(test_path)

    except ImportError as e:
        logger.error(f"PaddleOCR is not installed: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to download/verify model: {e}")
        return False
