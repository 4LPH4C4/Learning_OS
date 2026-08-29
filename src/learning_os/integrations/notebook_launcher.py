from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


class NotebookLaunchError(RuntimeError):
    pass


def launch_notebook(notebook_path: Path, project_root: Path) -> int:
    notebook_path = notebook_path.resolve()
    if not notebook_path.is_file() or notebook_path.suffix.lower() != ".ipynb":
        raise NotebookLaunchError(f"Notebook 파일을 찾을 수 없다: {notebook_path}")

    command = [
        sys.executable,
        "-m",
        "jupyter",
        "lab",
        str(notebook_path),
        "--notebook-dir",
        str(notebook_path.parent),
    ]
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    runtime_root = project_root / "data" / "jupyter"
    ipython_dir = runtime_root / "ipython"
    config_dir = runtime_root / "config"
    data_dir = runtime_root / "data"
    for directory in (ipython_dir, config_dir, data_dir):
        directory.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(
        {
            "IPYTHONDIR": str(ipython_dir),
            "JUPYTER_CONFIG_DIR": str(config_dir),
            "JUPYTER_DATA_DIR": str(data_dir),
        }
    )
    try:
        process = subprocess.Popen(
            command,
            cwd=project_root,
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            env=environment,
        )
    except OSError as exc:
        raise NotebookLaunchError(
            "JupyterLab을 시작하지 못했다. requirements 설치 상태를 확인해라."
        ) from exc
    return int(process.pid)
