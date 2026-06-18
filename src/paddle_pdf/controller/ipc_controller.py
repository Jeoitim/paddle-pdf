"""IPC controller — pytauri command endpoints for the GUI frontend.

Commands use pytauri's Commands API:
  - Each command receives `body: BaseModel` and `app_handle: AppHandle`
  - Returns a BaseModel (serialized to JSON) or bytes
  - Must be async and must not block
"""

import json
import os
import platform
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel
from pytauri import AppHandle, Emitter

from ..common.config import APP_NAME, APP_VERSION
from ..common.events import Events
from ..common.schemas import OcrOptions, TaskProgress
from ..service.model_service import ModelService
from ..service.system_service import SystemService
from ..service.task_queue import TaskQueue


# ── Request / Response Models ──────────────────────────────────

class EmptyBody(BaseModel):
    """For commands that take no meaningful parameters."""
    pass

class GreetRequest(BaseModel):
    name: str = "World"

class GreetResponse(BaseModel):
    message: str

class AppInfoResponse(BaseModel):
    name: str
    version: str
    python_version: str
    platform: str
    arch: str

class ProcessTaskRequest(BaseModel):
    task_id: str
    input_path: str
    model_name: str = "ch"
    use_gpu: bool = False
    dpi: int = 300
    max_pages: Optional[int] = None
    angle_cls: bool = True
    show_confidence: bool = False

class TaskResultResponse(BaseModel):
    success: bool
    input_path: Optional[str] = None
    output_pdf_path: Optional[str] = None
    output_txt_path: Optional[str] = None
    total_pages: int = 0
    total_lines: int = 0
    avg_confidence: float = 0.0
    elapsed_seconds: float = 0.0
    error: Optional[str] = None

class TaskProgressPayload(BaseModel):
    task_id: str
    status: str
    current_page: int = 0
    total_pages: int = 0
    message: str = ""
    elapsed: float = 0.0

class CancelTaskRequest(BaseModel):
    task_id: str

class DownloadModelRequest(BaseModel):
    name: str
    force: bool = False

class DownloadModelResponse(BaseModel):
    success: bool
    name: str

class GpuInfoResponse(BaseModel):
    available: bool = False
    cuda_version: Optional[str] = None
    cuda_root: Optional[str] = None
    device_count: int = 0
    error: Optional[str] = None

class OpenPathRequest(BaseModel):
    path: str

class SimpleResponse(BaseModel):
    success: bool
    error: Optional[str] = None


# ── Singleton services ─────────────────────────────────────────

_model_svc = ModelService()
_system_svc = SystemService()
_task_queue = TaskQueue(max_workers=1)


# ── Command Registration ───────────────────────────────────────

def register_commands_pytauri(commands: Any) -> None:
    """Register all IPC commands using pytauri's Commands API."""

    @commands.command()
    async def greet(body: GreetRequest) -> GreetResponse:
        return GreetResponse(message=f"Hello, {body.name}! {APP_NAME} v{APP_VERSION} is running.")

    @commands.command()
    async def get_app_info(body: EmptyBody) -> AppInfoResponse:
        return AppInfoResponse(
            name=APP_NAME,
            version=APP_VERSION,
            python_version=platform.python_version(),
            platform=platform.system(),
            arch=platform.machine(),
        )

    @commands.command()
    async def get_version(body: EmptyBody) -> bytes:
        return APP_VERSION.encode()

    @commands.command()
    async def process_task(body: ProcessTaskRequest, app_handle: AppHandle) -> SimpleResponse:
        """Submit a task to the background queue.  Returns immediately."""

        def _on_progress(task_id: str, tp: TaskProgress) -> None:
            try:
                Emitter.emit(
                    app_handle,
                    Events.TASK_PROGRESS,
                    TaskProgressPayload(
                        task_id=task_id,
                        status=tp.status.value,
                        current_page=tp.current_page,
                        total_pages=tp.total_pages,
                        message=tp.message,
                        elapsed=tp.elapsed,
                    ),
                )
            except Exception:
                pass

        # Wire up the progress callback (idempotent — safe to call repeatedly)
        _task_queue.set_progress_callback(_on_progress)

        opts = OcrOptions(
            model_name=body.model_name,
            use_gpu=body.use_gpu,
            dpi=body.dpi,
            max_pages=body.max_pages,
            angle_cls=body.angle_cls,
            show_confidence=body.show_confidence,
        )
        _task_queue.add_task(body.task_id, Path(body.input_path), opts)

        # Return immediately — task runs in background
        return SimpleResponse(success=True)

    @commands.command()
    async def cancel_task(body: CancelTaskRequest) -> SimpleResponse:
        ok = _task_queue.cancel_task(body.task_id)
        return SimpleResponse(success=ok)

    @commands.command()
    async def get_queue_status(body: EmptyBody) -> bytes:
        """Return JSON array of all task statuses."""
        return json.dumps(_task_queue.get_status()).encode()

    @commands.command()
    async def remove_task(body: CancelTaskRequest) -> SimpleResponse:
        """Remove a finished task from the queue store."""
        ok = _task_queue.remove_task(body.task_id)
        return SimpleResponse(success=ok)

    @commands.command()
    async def list_models(body: EmptyBody) -> bytes:
        models = [asdict(m) for m in _model_svc.list_models()]
        return json.dumps(models).encode()

    @commands.command()
    async def download_model(body: DownloadModelRequest) -> DownloadModelResponse:
        ok = _model_svc.download(body.name, force=body.force)
        return DownloadModelResponse(success=ok, name=body.name)

    @commands.command()
    async def check_gpu(body: EmptyBody) -> GpuInfoResponse:
        info = _system_svc.check_gpu()
        return GpuInfoResponse(
            available=info.available,
            cuda_version=info.cuda_version,
            cuda_root=info.cuda_root,
            device_count=info.device_count,
            error=info.error,
        )

    @commands.command()
    async def diagnose_system(body: EmptyBody) -> bytes:
        return json.dumps(_system_svc.diagnose()).encode()

    @commands.command()
    async def open_path(body: OpenPathRequest) -> SimpleResponse:
        try:
            if platform.system() == "Windows":
                os.startfile(body.path)
            elif platform.system() == "Darwin":
                import subprocess
                subprocess.Popen(["open", body.path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", body.path])
            return SimpleResponse(success=True)
        except Exception as e:
            return SimpleResponse(success=False, error=str(e))

    @commands.command()
    async def reveal_in_explorer(body: OpenPathRequest) -> SimpleResponse:
        try:
            if platform.system() == "Windows":
                import subprocess
                subprocess.Popen(["explorer", "/select,", body.path])
            elif platform.system() == "Darwin":
                import subprocess
                subprocess.Popen(["open", "-R", body.path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(Path(body.path).parent)])
            return SimpleResponse(success=True)
        except Exception as e:
            return SimpleResponse(success=False, error=str(e))
