"""Model registry and management for PaddleOCR."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from ..common.config import MODEL_CACHE_ROOT

logger = logging.getLogger(__name__)

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
    """Get the model cache directory."""
    return MODEL_CACHE_ROOT / name


def is_model_cached(name: str) -> bool:
    """Check if model is cached locally."""
    model_dir = get_model_dir(name)
    if not model_dir.exists():
        return False
    markers = ["inference", ".tar", "model"]
    for f in model_dir.rglob("*"):
        if any(marker in f.name for marker in markers):
            return True
    return False


def download_model(name: str, force: bool = False) -> bool:
    """Download/verify a PaddleOCR model."""
    if name not in MODEL_REGISTRY:
        logger.error(f"Unknown model: '{name}'")
        return False

    info = get_model_info(name)
    logger.info(f"Model: {name} - {info['desc']}")

    if is_model_cached(name) and not force:
        logger.info(f"Model '{name}' is already cached at {get_model_dir(name)}")
        return True

    logger.info(f"Downloading model '{name}'...")

    try:
        from paddleocr import PaddleOCR
        import warnings

        warnings.filterwarnings("ignore")
        ocr = PaddleOCR(lang=info["paddle_lang"])

        import numpy as np
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
