#!/usr/bin/env python3
"""
MercariBOT - Main entry point.
Auto-detects and seamlessly switches to the virtual environment (.venv) if present.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Auto-detect venv: automatically re-exec into .venv if present and not currently active
venv_dir = BASE_DIR / ".venv"
if Path(sys.prefix).resolve() != venv_dir.resolve() and venv_dir.exists():
    exe_name = Path(sys.executable).name
    win_python = venv_dir / "Scripts" / exe_name
    if not win_python.exists():
        win_python = venv_dir / "Scripts" / "python.exe"
    unix_python = venv_dir / "bin" / "python"
    target_python = win_python if os.name == "nt" else unix_python

    if target_python.exists():
        new_env = os.environ.copy()
        new_env["VIRTUAL_ENV"] = str(venv_dir)
        bin_dir = str(target_python.parent)
        new_env["PATH"] = f"{bin_dir}{os.pathsep}{new_env.get('PATH', '')}"
        os.execve(str(target_python), [str(target_python)] + sys.argv, new_env)

# Add src/ to sys.path
src_path = BASE_DIR / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    from mercaribot.cli import run
except ModuleNotFoundError as e:
    print(f"\nError: Missing dependency ({e.name}).")
    print("Install dependencies with:")
    print("   pip install -r requirements.txt")
    print("or use the automatic launcher:")
    print("   ./run.sh  (Linux / macOS)")
    print("   run.bat   (Windows)\n")
    sys.exit(1)

if __name__ == "__main__":
    run()
