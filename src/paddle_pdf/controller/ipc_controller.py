"""IPC controller — pytauri command endpoints for the GUI frontend.

All commands accept simple JSON-serializable args and return dicts.
The frontend calls these via `invoke("command_name", {args})`.
"""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..common.schemas import OcrOptions, TaskProgress, TaskStatus
from ..common.events import Events
from ..service.ocr_service import OcrService
from ..service.model_service import ModelService
from ..service.system_service import SystemService


# Singleton services (stateless wrappers, safe to reuse)
_model_svc = ModelService()
_system_svc = SystemService()

# Active task reference (single-task model for now)
_active_service: OcrService | None = None


def register_commands(commands: Any, app_handle: Any) -> None:
    """Register all IPC commands on the pytauri Commands object.

    Args:
        commands: pytauri Commands instance
        app_handle: Tauri AppHandle for emitting events
    """

    @commands.command()
    async def process_task(input_path: str, options: dict[str, Any]) -> dict[str, Any]:
        """Start an OCR task. Emits progress events via app_handle."""
        nonlocal _active_service
        _active_service = OcrService()

        opts = OcrOptions(
            model_name=options.get("model_name", "ch"),
            use_gpu=options.get("use_gpu", False),
            dpi=options.get("dpi", 300),
            max_pages=options.get("max_pages"),
            angle_cls=options.get("angle_cls", True),
            show_confidence=options.get("show_confidence", False),
        )

        def _on_progress(tp: TaskProgress):
            app_handle.emit(
                Events.TASK_PROGRESS,
                {
                    "status": tp.status.value,
                    "current_page": tp.current_page,
                    "total_pages": tp.total_pages,
                    "message": tp.message,
                    "elapsed": tp.elapsed,
                },
            )

        try:
            result = _active_service.process_pdf(
                input_path=Path(input_path),
                options=opts,
                progress_callback=_on_progress,
            )
            app_handle.emit(
                Events.TASK_COMPLETED,
                {
                    "input_path": str(result.input_path),
                    "output_pdf_path": str(result.output_pdf_path) if result.output_pdf_path else None,
                    "output_txt_path": str(result.output_txt_path) if result.output_txt_path else None,
                    "total_pages": result.total_pages,
                    "total_lines": result.total_lines,
                    "avg_confidence": result.avg_confidence,
                    "elapsed_seconds": result.elapsed_seconds,
                },
            )
            return {
                "success": True,
                "result": {
                    "input_path": str(result.input_path),
                    "output_pdf_path": str(result.output_pdf_path) if result.output_pdf_path else None,
                    "output_txt_path": str(result.output_txt_path) if result.output_txt_path else None,
                    "total_pages": result.total_pages,
                    "total_lines": result.total_lines,
                    "avg_confidence": result.avg_confidence,
                    "elapsed_seconds": result.elapsed_seconds,
                },
            }
        except Exception as e:
            app_handle.emit(Events.TASK_FAILED, {"error": str(e)})
            return {"success": False, "error": str(e)}
        finally:
            _active_service = None

    @commands.command()
    async def cancel_task() -> dict[str, Any]:
        """Cancel the currently running task."""
        if _active_service:
            _active_service.cancel()
            return {"success": True}
        return {"success": False, "error": "No active task"}

    @commands.command()
    async def list_models() -> list[dict[str, Any]]:
        """Return all available models with cache status."""
        return [asdict(m) for m in _model_svc.list_models()]

    @commands.command()
    async def check_gpu() -> dict[str, Any]:
        """Check GPU availability."""
        info = _system_svc.check_gpu()
        return asdict(info)

    @commands.command()
    async def diagnose_system() -> dict[str, str]:
        """Full system diagnosis."""
        return _system_svc.diagnose()

    @commands.command()
    async def download_model(name: str, force: bool = False) -> dict[str, Any]:
        """Download a specific model."""
        ok = _model_svc.download(name, force=force)
        return {"success": ok, "name": name}

    @commands.command()
    async def select_file() -> dict[str, Any]:
        """Open native file dialog. Returns selected path or None."""
        # This will be handled by Tauri's dialog API on the frontend side.
        # This command exists as a fallback / convenience.
        return {"path": None, "note": "Use Tauri dialog API from frontend"}

    @commands.command()
    async def open_path(path: str) -> dict[str, Any]:
        """Open a file or folder in the system file manager."""
        try:
            os.startfile(path)  # Windows
        except AttributeError:
            import subprocess
            subprocess.Popen(["xdg-open", path])  # Linux / macOS
        return {"success": True}

    @commands.command()
    async def get_version() -> str:
        """Return app version."""
        from ..common.config import APP_VERSION
        return APP_VERSION
