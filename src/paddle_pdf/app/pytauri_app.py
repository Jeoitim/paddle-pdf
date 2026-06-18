"""pytauri application entry point.

This module is loaded by the Tauri Rust binary via PythonInterpreterBuilder.
It registers all IPC commands and runs the Tauri app.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on sys.path so paddle_pdf is importable
_src_dir = str(Path(__file__).resolve().parent.parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


def main() -> None:
    """Build and run the Tauri app with pytauri."""
    from anyio.from_thread import start_blocking_portal
    from pytauri import Builder, BuilderArgs, Commands, context_factory, builder_factory

    # Create commands registry and register all IPC commands
    commands = Commands()
    from paddle_pdf.controller.ipc_controller import register_commands_pytauri
    register_commands_pytauri(commands)

    # Build and run the Tauri app
    with start_blocking_portal(backend="asyncio") as portal:
        invoke_handler = commands.generate_handler(portal)
        context = context_factory()
        builder = builder_factory()
        args = BuilderArgs(context, invoke_handler=invoke_handler)
        app = builder.build(args)
        app.run()


if __name__ == "__main__":
    main()
