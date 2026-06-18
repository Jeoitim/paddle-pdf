"""pytauri application entry point.

This module is loaded by the Tauri Rust sidecar via pytauri.
It registers all IPC commands and starts the app.
"""

from __future__ import annotations

from pytauri import Commands


def main() -> None:
    """Initialize and run the pytauri app."""
    commands = Commands()

    # Import and register IPC commands
    # The app_handle is provided by pytauri at runtime
    from pytauri import app_handle
    from ..controller.ipc_controller import register_commands

    register_commands(commands, app_handle)

    # Start the Tauri app (blocking)
    from pytauri import PyTauri

    py_tauri = PyTauri()
    py_tauri.run()
