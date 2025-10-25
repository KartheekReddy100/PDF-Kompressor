from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import urllib.request
from typing import Optional

from .ghostscript_finder import get_ghostscript_path


GITHUB_RELEASE_API = "https://api.github.com/repos/ArtifexSoftware/ghostpdl-downloads/releases/latest"


def _arch_tag() -> str:
    # Prefer 64-bit on modern Windows
    return "w64" if platform.architecture()[0] == "64bit" else "w32"


def _guess_asset_name_pattern(arch: str) -> re.Pattern[str]:
    # Typical asset names: gs10040w64.exe or gs10040w32.exe
    return re.compile(rf"gs\d{{5}}{arch}\.exe$", re.IGNORECASE)


def _fetch_latest_download_url(arch: str, timeout: int = 20) -> Optional[str]:
    # Query GitHub releases to find the direct asset URL for the desired arch
    try:
        req = urllib.request.Request(GITHUB_RELEASE_API, headers={"User-Agent": "pdf-compressor"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
        assets = data.get("assets", [])
        pat = _guess_asset_name_pattern(arch)
        for a in assets:
            name = a.get("name", "")
            browser_url = a.get("browser_download_url")
            if pat.search(name) and browser_url and browser_url.endswith(".exe"):
                return browser_url
    except Exception:
        return None
    return None


def _download_to_temp(url: str, timeout: int = 60) -> Optional[str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            fd, path = tempfile.mkstemp(prefix="gs-setup-", suffix=".exe")
            with os.fdopen(fd, "wb") as f:
                shutil.copyfileobj(resp, f)
        return path
    except Exception:
        return None


def _run_installer(installer_path: str, silent: bool = True, timeout: int = 600) -> bool:
    # Many Ghostscript installers support /S (NSIS/Inno Setup style). Try silent then fallback.
    try:
        args = [installer_path, "/S"] if silent else [installer_path]
        proc = subprocess.run(args, check=False, timeout=timeout)
        if proc.returncode == 0:
            return True
        if silent:
            # Retry without silent to allow UI interaction
            proc2 = subprocess.run([installer_path], check=False, timeout=timeout)
            return proc2.returncode == 0
        return False
    except Exception:
        return False


def ensure_ghostscript_installed(auto_install: bool = False) -> Optional[str]:
    """Ensure Ghostscript is installed; optionally auto-install if missing.

    Returns the Ghostscript path if available/installed, else None.
    """
    gs = get_ghostscript_path()
    if gs:
        return gs
    if not auto_install:
        return None

    arch = _arch_tag()
    url = _fetch_latest_download_url(arch)
    if not url:
        return None

    installer = _download_to_temp(url)
    if not installer:
        return None
    try:
        ok = _run_installer(installer, silent=True)
        if not ok:
            return None
    finally:
        try:
            os.remove(installer)
        except Exception:
            pass

    # Re-detect after install
    return get_ghostscript_path()
