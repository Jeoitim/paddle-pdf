"""HTTP backend server for PaddlePDF.

Replaces pytauri IPC. The Tauri frontend communicates with this process via HTTP.
Push events (progress, completion, failure) are delivered through Server-Sent Events (SSE).

Entry point for PyInstaller packaging.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import signal
import sys
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# -- Logging -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("paddle_pdf.backend")

# -- Ensure src/ is importable (for development without install) ---------------
_this_dir = Path(__file__).resolve().parent
if getattr(sys, "frozen", False):
    _base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    _base = _this_dir.parent.parent.parent  # .../src/

if str(_base) not in sys.path:
    sys.path.insert(0, str(_base))

# -- App & Services ------------------------------------------------------------
from paddle_pdf.common.config import APP_NAME, APP_VERSION
from paddle_pdf.common.events import Events
from paddle_pdf.common.schemas import OcrOptions
from paddle_pdf.service.model_service import ModelService
from paddle_pdf.service.system_service import SystemService
from paddle_pdf.service.task_queue import TaskQueue

app = FastAPI(title="PaddlePDF Backend", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_model_svc = ModelService()
_system_svc = SystemService()
_task_queue = TaskQueue(max_workers=1)

# -- SSE event bus -------------------------------------------------------------
_sse_clients: dict[str, asyncio.Queue] = {}


def _push_event(event_type: str, data: Any) -> None:
    payload = json.dumps({"type": event_type, "data": data})
    dead = []
    for cid, q in _sse_clients.items():
        try:
            q.put_nowait({"event": event_type, "data": payload})
        except asyncio.QueueFull:
            dead.append(cid)
    for cid in dead:
        _sse_clients.pop(cid, None)


def _on_progress(task_id: str, tp) -> None:
    _push_event(Events.TASK_PROGRESS, {
        "task_id": task_id, "status": tp.status.value,
        "current_page": tp.current_page, "total_pages": tp.total_pages,
        "message": tp.message, "elapsed": tp.elapsed,
    })


def _on_completed(task_id: str, result) -> None:
    _push_event(Events.TASK_COMPLETED, {
        "task_id": task_id, "success": True,
        "input_path": str(result.input_path),
        "output_pdf_path": str(result.output_pdf_path) if result.output_pdf_path else "",
        "output_txt_path": str(result.output_txt_path) if result.output_txt_path else "",
        "total_pages": result.total_pages, "total_lines": result.total_lines,
        "avg_confidence": result.avg_confidence, "elapsed_seconds": result.elapsed_seconds,
    })


def _on_failed(task_id: str, error: str) -> None:
    _push_event(Events.TASK_FAILED, {"task_id": task_id, "success": False, "error": error})


def _on_cancelled(task_id: str) -> None:
    _push_event(Events.TASK_CANCELLED, {"task_id": task_id, "success": False, "error": "Cancelled by user"})


_task_queue.set_progress_callback(_on_progress)
_task_queue.set_completion_callback(_on_completed)
_task_queue.set_failure_callback(_on_failed)
_task_queue.set_cancel_callback(_on_cancelled)


# -- Request / Response Models -------------------------------------------------
class ProcessTaskRequest(BaseModel):
    task_id: str; input_path: str; model_name: str = "ch"
    use_gpu: bool = False; dpi: int = 300; max_pages: Optional[int] = None
    angle_cls: bool = True; show_confidence: bool = False

class CancelTaskRequest(BaseModel):
    task_id: str

class DownloadModelRequest(BaseModel):
    name: str; force: bool = False

class OpenPathRequest(BaseModel):
    path: str

class SimpleResponse(BaseModel):
    success: bool; error: Optional[str] = None


# -- Routes --------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "version": APP_VERSION}

@app.get("/app_info")
async def get_app_info():
    return {"name": APP_NAME, "version": APP_VERSION,
            "python_version": platform.python_version(),
            "platform": platform.system(), "arch": platform.machine()}

@app.get("/events")
async def sse_stream(request: Request):
    client_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    _sse_clients[client_id] = queue

    async def generator():
        try:
            yield f"event: connected\ndata: {json.dumps({'client_id': client_id})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: {item['event']}\ndata: {item['data']}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            _sse_clients.pop(client_id, None)

    return StreamingResponse(generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.post("/process_task", response_model=SimpleResponse)
async def process_task(body: ProcessTaskRequest):
    opts = OcrOptions(model_name=body.model_name, use_gpu=body.use_gpu, dpi=body.dpi,
        max_pages=body.max_pages, angle_cls=body.angle_cls, show_confidence=body.show_confidence)
    _task_queue.add_task(body.task_id, Path(body.input_path), opts)
    return SimpleResponse(success=True)

@app.post("/cancel_task", response_model=SimpleResponse)
async def cancel_task(body: CancelTaskRequest):
    return SimpleResponse(success=_task_queue.cancel_task(body.task_id))

@app.post("/remove_task", response_model=SimpleResponse)
async def remove_task(body: CancelTaskRequest):
    return SimpleResponse(success=_task_queue.remove_task(body.task_id))

@app.get("/queue_status")
async def get_queue_status():
    return _task_queue.get_status()

@app.get("/list_models")
async def list_models():
    return [asdict(m) for m in _model_svc.list_models()]

@app.post("/download_model")
async def download_model(body: DownloadModelRequest):
    ok = _model_svc.download(body.name, force=body.force)
    return {"success": ok, "name": body.name}

@app.get("/check_gpu")
async def check_gpu():
    info = _system_svc.check_gpu()
    return {"available": info.available, "cuda_version": info.cuda_version,
            "cuda_root": info.cuda_root, "device_count": info.device_count, "error": info.error}

@app.get("/diagnose_system")
async def diagnose_system():
    return _system_svc.diagnose()

@app.post("/open_path", response_model=SimpleResponse)
async def open_path(body: OpenPathRequest):
    try:
        if platform.system() == "Windows":
            os.startfile(body.path)
        elif platform.system() == "Darwin":
            import subprocess; subprocess.Popen(["open", body.path])
        else:
            import subprocess; subprocess.Popen(["xdg-open", body.path])
        return SimpleResponse(success=True)
    except Exception as e:
        return SimpleResponse(success=False, error=str(e))

@app.post("/reveal_in_explorer", response_model=SimpleResponse)
async def reveal_in_explorer(body: OpenPathRequest):
    try:
        if platform.system() == "Windows":
            import subprocess; subprocess.Popen(["explorer", "/select,", body.path])
        elif platform.system() == "Darwin":
            import subprocess; subprocess.Popen(["open", "-R", body.path])
        else:
            import subprocess; subprocess.Popen(["xdg-open", str(Path(body.path).parent)])
        return SimpleResponse(success=True)
    except Exception as e:
        return SimpleResponse(success=False, error=str(e))

@app.post("/shutdown")
async def shutdown():
    logger.info("Shutdown requested by Tauri frontend")
    _task_queue.shutdown(wait=False)
    async def _do_shutdown():
        await asyncio.sleep(0.3)
        os._exit(0)
    asyncio.create_task(_do_shutdown())
    return {"ok": True}


# -- Entry point ---------------------------------------------------------------
def main() -> None:
    import socket
    import threading
    import ctypes
    import time

    parent_pid_str = os.environ.get("PADDLE_PDF_PARENT_PID")
    if parent_pid_str:
        try:
            parent_pid = int(parent_pid_str)

            def watch_parent_lifetime() -> None:
                if platform.system() == "Windows":
                    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                    kernel32 = ctypes.windll.kernel32
                    while True:
                        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, parent_pid)
                        if handle:
                            exit_code = ctypes.c_ulong()
                            kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                            kernel32.CloseHandle(handle)
                            if exit_code.value != 259: # 259 is STILL_ACTIVE
                                break
                        else:
                            break
                        time.sleep(1)
                else:
                    while True:
                        try:
                            os.kill(parent_pid, 0)
                        except OSError:
                            break
                        time.sleep(1)

                logger.info("Parent process %d exited. Shutting down.", parent_pid)
                os._exit(0)

            t = threading.Thread(target=watch_parent_lifetime, daemon=True)
            t.start()
        except Exception as e:
            logger.error("Failed to start parent process watcher: %s", e)

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    # Print port to stdout — Tauri reads this to know where to connect
    print(f"PADDLE_PDF_PORT={port}", flush=True)
    logger.info("PaddlePDF backend starting on http://127.0.0.1:%d", port)

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
