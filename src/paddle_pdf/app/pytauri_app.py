"""pytauri application entry point.

This module is loaded by the Tauri Rust sidecar via pytauri.
It registers all IPC commands and starts the app.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the src/ directory is on sys.path so paddle_pdf is importable
_src_dir = str(Path(__file__).resolve().parent.parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


def main() -> None:
    """Initialize and run the pytauri app."""
    from pytauri import Commands
    from pytauri import app_handle

    commands = Commands()

    # Register all IPC commands from the controller layer
    from paddle_pdf.controller.ipc_controller import register_commands

    register_commands(commands, app_handle)

    # Run the Tauri event loop (blocking)
    from pytauri import PyTauri

    py_tauri = PyTauri()
    py_tauri.run()
