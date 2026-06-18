"""
Model Registry and Management for PaddleOCR
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional

MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
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


def get_model_info(name: str) -> Dict[str, Any]:
    """Get information about a model."""
    return MODEL_REGISTRY.get(name, MODEL_REGISTRY["ch"]).copy()


def list_models() -> List[Dict[str, str]]:
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
    return Path.home() / ".paddleocr" / "ocr" / name


def is_model_cached(name: str) -> bool:
    """Check if model is cached locally."""
    model_dir = get_model_dir(name)
    if not model_dir.exists():
        return False
    # Check for model files
    markers = ["inference", ".tar", "model"]
    return any(
        any(marker in f.name for m in model_dir.rglob("*") for marker in markers)
        for _ in [None]
        if any(model_dir.rglob("*"))
    )


def download_model(name: str, force: bool = False) -> bool:
    """
    Download/verify a PaddleOCR model.

    PaddleOCR automatically downloads models on first use.
    This function triggers the download with proper error handling.
    """
    if name not in MODEL_REGISTRY:
        print(f"[ERROR] Unknown model: '{name}'")
        print(f"Available models: {', '.join(MODEL_REGISTRY.keys())}")
        return False

    info = get_model_info(name)
    print(f"Model: {name} - {info['desc']}")

    # Check if already cached
    if is_model_cached(name) and not force:
        print(f"[OK] Model '{name}' is already cached at {get_model_dir(name)}")
        return True

    print(f"Downloading model '{name}'...")
    print("  (PaddleOCR downloads models automatically on first use)")
    print("  If download is slow, ensure internet connection is active.")

    try:
        # Import and trigger model download
        from paddleocr import PaddleOCR
        import warnings

        warnings.filterwarnings("ignore")

        # Initialize to trigger download
        # Note: use_gpu is determined by PaddlePaddle installation, not PaddleOCR params
        ocr = PaddleOCR(lang=info["paddle_lang"])

        # Try a minimal recognition to verify model is loaded
        # Use a blank image as test
        import numpy as np
        from PIL import Image
        import tempfile

        # Create a minimal test image
        test_img = Image.new("RGB", (100, 100), color="white")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            test_path = f.name
            test_img.save(test_path)

        try:
            result = ocr.ocr(test_path)
            print(f"[OK] Model '{name}' is ready!")
            return True
        finally:
            os.unlink(test_path)

    except ImportError as e:
        print(f"[ERROR] PaddleOCR is not installed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to download/verify model: {e}")
        print(f"  The model may not exist in the PaddleOCR model zoo.")
        print(
            f"  Try a different model (ch, ch_plus, en) or install PaddleOCR properly:"
        )
        print(f"    uv pip install paddleocr paddlepaddle")
        return False
