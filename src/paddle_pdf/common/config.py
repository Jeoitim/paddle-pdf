"""Global configuration constants."""

from pathlib import Path

APP_NAME = "PaddlePDF"
APP_VERSION = "1.0.0"

# Default OCR settings
DEFAULT_MODEL = "ch"
DEFAULT_DPI = 300
DEFAULT_MAX_PAGES = 0  # 0 = all pages

# Model cache root
MODEL_CACHE_ROOT = Path.home() / ".paddleocr" / "ocr"
