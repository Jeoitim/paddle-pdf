"""IPC controller — pytauri command endpoints for the GUI frontend.

All commands accept simple JSON-serializable args and return dicts.
The frontend calls these via `invoke("command_name", {args})`.
"""

from __future__ import annotations

import os
import platform
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..common.schemas import OcrOptions, TaskProgress, TaskStatus
from ..common.events import Events
from ..common.config import APP_NAME, APP_VERSION
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

    # ── Test / Info ──────────────────────────────────────────────

    @commands.command()
    async def greet(name: str = "World") -> str:
        """Test command — verify IPC round-trip works."""
        return f"Hello, {name}! {APP_NAME} v{APP_VERSION} is running."

    @commands.command()
    async def get_app_info() -> dict[str, Any]:
        """Return app metadata for the frontend header/about dialog."""
        return {
            "name": APP_NAME,
            "version": APP_VERSION,
            "python_version": platform.python_version(),
            "platform": platform.system(),
            "arch": platform.machine(),
        }

    @commands.command()
    async def get_version() -> str:
        """Return app version string."""
        return APP_VERSION

    # ── OCR Processing ───────────────────────────────────────────

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
            try:
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
            except Exception:
                pass  # Don't let emit errors crash the processing

        try:
            result = _active_service.process_pdf(
                input_path=Path(input_path),
                options=opts,
                progress_callback=_on_progress,
            )
            result_dict = {
                "input_path": str(result.input_path),
                "output_pdf_path": str(result.output_pdf_path) if result.output_pdf_path else None,
                "output_txt_path": str(result.output_txt_path) if result.output_txt_path else None,
                "total_pages": result.total_pages,
                "total_lines": result.total_lines,
                "avg_confidence": result.avg_confidence,
                "elapsed_seconds": result.elapsed_seconds,
            }
            try:
                app_handle.emit(Events.TASK_COMPLETED, result_dict)
            except Exception:
                pass
            return {"success": True, "result": result_dict}
        except InterruptedError:
            return {"success": False, "error": "Cancelled by user"}
        except Exception as e:
            error_dict = {"error": str(e)}
            try:
                app_handle.emit(Events.TASK_FAILED, error_dict)
            except Exception:
                pass
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

    # ── Models ───────────────────────────────────────────────────

    @commands.command()
    async def list_models() -> list[dict[str, Any]]:
        """Return all available models with cache status."""
        return [asdict(m) for m in _model_svc.list_models()]

    @commands.command()
    async def download_model(name: str, force: bool = False) -> dict[str, Any]:
        """Download a specific model."""
        ok = _model_svc.download(name, force=force)
        return {"success": ok, "name": name}

    # ── System ───────────────────────────────────────────────────

    @commands.command()
    async def check_gpu() -> dict[str, Any]:
        """Check GPU availability."""
        info = _system_svc.check_gpu()
        return asdict(info)

    @commands.command()
    async def diagnose_system() -> dict[str, str]:
        """Full system diagnosis."""
        return _system_svc.diagnose()

    # ── File System ──────────────────────────────────────────────

    @commands.command()
    async def select_file() -> dict[str, Any]:
        """Open native file dialog. Returns selected path or None."""
        # The frontend uses Tauri's dialog API directly.
        # This command is a fallback.
        return {"path": None, "note": "Use Tauri dialog API from frontend"}

    @commands.command()
    async def open_path(path: str) -> dict[str, Any]:
        """Open a file or folder in the system file manager."""
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                import subprocess
                subprocess.Popen(["open", path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @commands.command()
    async def reveal_in_explorer(path: str) -> dict[str, Any]:
        """Open the containing folder and select the file."""
        try:
            if platform.system() == "Windows":
                import subprocess
                subprocess.Popen(["explorer", "/select,", path])
            elif platform.system() == "Darwin":
                import subprocess
                subprocess.Popen(["open", "-R", path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(Path(path).parent)])
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
