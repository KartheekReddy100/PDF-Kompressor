from __future__ import annotations

import os
import sys
import datetime as _dt
from typing import Optional


def _base_dir() -> str:
    try:
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()


def get_log_path() -> str:
    base = _base_dir()
    logs_dir = os.path.join(base, "logs")
    try:
        os.makedirs(logs_dir, exist_ok=True)
    except Exception:
        # Fall back to temp folder
        return os.path.join(base, f"app-error-{_dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.log")
    return os.path.join(logs_dir, "app.log")


def safe_log(message: str) -> Optional[str]:
    try:
        path = get_log_path()
        with open(path, "a", encoding="utf-8") as f:
            ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{ts}] {message}\n")
        return path
    except Exception:
        return None
