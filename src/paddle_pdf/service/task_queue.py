"""Background task queue — processes OCR tasks sequentially with per-task isolation.

Design:
- Tasks are submitted via ``add_task()`` and return immediately.
- A background worker thread picks up the next pending task when capacity allows.
- Each task gets its own ``OcrService`` instance (model isolation).
- Progress is reported back via a callback that routes events by ``task_id``.
- ``max_workers`` defaults to 1 (sequential) — GPU memory rarely allows concurrent models.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from ..common.schemas import OcrOptions, TaskProgress, TaskResult, TaskStatus

logger = logging.getLogger(__name__)

# Type alias for the progress callback: (task_id, TaskProgress) -> None
ProgressCallback = Callable[[str, TaskProgress], None]


@dataclass
class QueuedTask:
    """Internal representation of a task in the queue."""

    task_id: str
    input_path: Path
    options: OcrOptions
    status: TaskStatus = TaskStatus.PENDING
    progress: Optional[TaskProgress] = None
    result: Optional[TaskResult] = None
    error: Optional[str] = None


class TaskQueue:
    """Background task queue with sequential (or bounded-parallel) execution.

    Thread-safety: all mutations to ``_tasks`` / ``_queue`` / ``_active`` are
    guarded by ``_lock``.  The actual OCR work runs in ``_executor`` threads.
    """

    def __init__(self, max_workers: int = 1) -> None:
        self._tasks: dict[str, QueuedTask] = {}
        self._queue: list[str] = []  # task_ids waiting to run (FIFO)
        self._active: dict[str, Any] = {}  # task_id -> OcrService
        self._max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.Lock()
        self._progress_callback: ProgressCallback | None = None

    # ── public API ────────────────────────────────────────────

    def set_progress_callback(self, cb: ProgressCallback | None) -> None:
        """Register the callback that forwards progress events to the frontend."""
        self._progress_callback = cb

    def add_task(self, task_id: str, input_path: Path, options: OcrOptions) -> QueuedTask:
        """Enqueue a new task.  Returns immediately; the task starts when capacity allows."""
        with self._lock:
            task = QueuedTask(task_id=task_id, input_path=input_path, options=options)
            self._tasks[task_id] = task
            self._queue.append(task_id)
            logger.info("Task %s enqueued (%d ahead)", task_id, len(self._queue) - 1)
            self._try_start_next()
            return task

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task — either stop it if running, or remove it from the queue."""
        with self._lock:
            if task_id in self._active:
                self._active[task_id].cancel()
                logger.info("Task %s cancel signal sent", task_id)
                return True
            if task_id in self._queue:
                self._queue.remove(task_id)
                self._tasks[task_id].status = TaskStatus.CANCELLED
                logger.info("Task %s removed from queue", task_id)
                return True
            return False

    def get_status(self) -> list[dict[str, Any]]:
        """Snapshot of every task's status (for ``get_queue_status`` IPC)."""
        with self._lock:
            return [
                {
                    "task_id": t.task_id,
                    "status": t.status.value,
                    "current_page": t.progress.current_page if t.progress else 0,
                    "total_pages": t.progress.total_pages if t.progress else 0,
                    "message": t.progress.message if t.progress else "",
                    "elapsed": t.progress.elapsed if t.progress else 0.0,
                    "error": t.error,
                }
                for t in self._tasks.values()
            ]

    def get_task(self, task_id: str) -> QueuedTask | None:
        with self._lock:
            return self._tasks.get(task_id)

    def remove_task(self, task_id: str) -> bool:
        """Remove a completed / failed / cancelled task from the store."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status in (
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ):
                del self._tasks[task_id]
                return True
            return False

    def shutdown(self, wait: bool = True) -> None:
        """Shut down the executor.  Cancels running tasks if ``wait=False``."""
        self._executor.shutdown(wait=wait)

    # ── internal ──────────────────────────────────────────────

    def _try_start_next(self) -> None:
        """Pick the next pending task if we have capacity.  Must be called under ``_lock``."""
        if len(self._active) >= self._max_workers:
            return
        while self._queue:
            task_id = self._queue.pop(0)
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                self._start_task(task)
                break

    def _start_task(self, task: QueuedTask) -> None:
        """Submit a task to the thread pool.  Must be called under ``_lock``."""
        # Import here to avoid circular import at module level
        from .ocr_service import OcrService

        task.status = TaskStatus.EXTRACTING
        service = OcrService()
        self._active[task.task_id] = service
        logger.info("Task %s started", task.task_id)
        self._executor.submit(self._run_task, task, service)

    def _run_task(self, task: QueuedTask, service: Any) -> None:
        """Worker that runs inside the thread pool."""
        try:
            def _on_progress(tp: TaskProgress) -> None:
                task.progress = tp
                if self._progress_callback:
                    try:
                        self._progress_callback(task.task_id, tp)
                    except Exception:
                        pass

            result = service.process_pdf(
                input_path=task.input_path,
                options=task.options,
                progress_callback=_on_progress,
            )
            task.result = result
            task.status = TaskStatus.COMPLETED
            logger.info("Task %s completed", task.task_id)

        except InterruptedError:
            task.status = TaskStatus.CANCELLED
            logger.info("Task %s cancelled", task.task_id)

        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            logger.exception("Task %s failed", task.task_id)

        finally:
            with self._lock:
                self._active.pop(task.task_id, None)
                self._try_start_next()
