"""IPC event name constants — single source of truth for frontend ↔ backend."""


class Events:
    TASK_PROGRESS = "task://progress"
    TASK_COMPLETED = "task://completed"
    TASK_FAILED = "task://failed"
    TASK_CANCELLED = "task://cancelled"
    QUEUE_STATUS = "queue://status"
    MODEL_DOWNLOAD_PROGRESS = "model://download_progress"
