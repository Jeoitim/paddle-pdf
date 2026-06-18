"""Data structures shared across layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class TaskStatus(Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    OCR_RUNNING = "ocr_running"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OcrOptions:
    """OCR processing options, shared by CLI and GUI."""

    model_name: str = "ch"
    use_gpu: bool = False
    dpi: int = 300
    max_pages: int | None = None
    angle_cls: bool = True
    show_confidence: bool = False


@dataclass
class PageResult:
    """OCR result for a single page."""

    page_num: int
    image_path: str
    ocr_results: list[dict[str, Any]] = field(default_factory=list)
    num_lines: int = 0
    avg_confidence: float = 0.0
    elapsed: float = 0.0
    error: str | None = None


@dataclass
class TaskResult:
    """Final result of an OCR task."""

    input_path: Path
    output_pdf_path: Path | None = None
    output_txt_path: Path | None = None
    total_pages: int = 0
    total_lines: int = 0
    avg_confidence: float = 0.0
    elapsed_seconds: float = 0.0
    pages: list[PageResult] = field(default_factory=list)


@dataclass
class TaskProgress:
    """Progress update emitted during processing."""

    status: TaskStatus
    current_page: int = 0
    total_pages: int = 0
    message: str = ""
    elapsed: float = 0.0


@dataclass
class GpuInfo:
    """GPU environment information."""

    available: bool = False
    cuda_version: str | None = None
    cuda_root: str | None = None
    device_count: int = 0
    error: str | None = None


@dataclass
class ModelInfo:
    """Model metadata."""

    name: str
    desc: str
    lang: str
    model_type: str = ""
    note: str = ""
    cached: bool = False
