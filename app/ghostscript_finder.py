import os
import sys
import shutil
import glob
from typing import Optional


def _which_any(candidates: list[str]) -> Optional[str]:
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    return None


def _probe_common_windows_paths() -> Optional[str]:
    # Typical install locations, e.g. C:\\Program Files\\gs\\gs10.04.0\\bin\\gswin64c.exe
    patterns = [
        r"C:\\Program Files\\gs\\gs*\\bin\\gswin64c.exe",
        r"C:\\Program Files\\gs\\gs*\\bin\\gswin32c.exe",
        r"C:\\Program Files (x86)\\gs\\gs*\\bin\\gswin64c.exe",
        r"C:\\Program Files (x86)\\gs\\gs*\\bin\\gswin32c.exe",
    ]
    candidates: list[str] = []
    for pattern in patterns:
        candidates.extend(glob.glob(pattern))
    # Prefer 64-bit console version if present
    candidates_sorted = sorted(
        candidates,
        key=lambda p: ("64c" not in os.path.basename(p), p),
    )
    return candidates_sorted[0] if candidates_sorted else None


def get_ghostscript_path() -> Optional[str]:
    """Return the full path to the Ghostscript console executable (gswin64c/gswin32c) if available."""
    # 0) Look for a bundled Ghostscript next to the executable (portable distribution)
    potential_roots: list[str] = []
    try:
        if getattr(sys, 'frozen', False):
            # PyInstaller onefile/onedir
            base = getattr(sys, '_MEIPASS', None) or os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        # Expect structure ghostscript/bin/gswin64c.exe
        potential_roots.append(os.path.join(base, 'ghostscript'))
        # Also check next to the executable for a sibling folder
        potential_roots.append(os.path.join(os.path.dirname(sys.executable) if hasattr(sys, 'executable') else base, 'ghostscript'))
    except Exception:
        pass

    for root in potential_roots:
        for name in ("gswin64c.exe", "gswin32c.exe"):
            p = os.path.join(root, "bin", name)
            if os.path.exists(p):
                return p

    # 1) Try PATH
    path = _which_any(["gswin64c", "gswin64c.exe", "gswin32c", "gswin32c.exe", "gs"])
    if path:
        return path
    # 2) Try common Windows install locations
    path = _probe_common_windows_paths()
    if path and os.path.exists(path):
        return path
    return None
