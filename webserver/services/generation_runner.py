from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def launch_detached_command(command: list[str], cwd: Path | str | None = None) -> None:
    if not command:
        raise ValueError("command must not be empty")

    resolved_cwd = None if cwd is None else str(Path(cwd))
    creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    launch_command = [str(part) for part in command]
    if sys.platform.startswith("win"):
        launch_command = ["cmd", "/c", *launch_command]

    subprocess.Popen(
        launch_command,
        cwd=resolved_cwd,
        creationflags=creation_flags,
    )


def launch_generation(repo_root: Path) -> None:
    repo_root = Path(repo_root)
    command = [sys.executable, "action_make_all.py"]
    if sys.platform.startswith("win"):
        command = ["cmd", "/k", *command]

    subprocess.Popen(
        [str(part) for part in command],
        cwd=str(repo_root),
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
    )
