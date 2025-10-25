<div align="center">

# PDF Kompressor (GUI) for Windows

[![Windows](https://img.shields.io/badge/OS-Windows-blue)](#)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](#)
[![GUI](https://img.shields.io/badge/GUI-Tkinter-44CC11)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A simple, friendly PDF compressor for Windows with a Tkinter GUI.

</div>

- Best compression (recommended): uses Ghostscript if available
- Basic compression (no external tools): uses pure-Python fallback (pikepdf) to shrink streams and optimize structure

Works on Windows (PowerShell). Linux/macOS can work too with small adjustments.

## Table of contents

- [Features](#features)
- [Requirements](#requirements)
- [Setup](#setup)
- [Run the GUI](#run-the-gui)
- [Make a Windows EXE (optional)](#make-a-windows-exe-optional)
- [Make a portable ZIP with Ghostscript included](#make-a-portable-zip-with-ghostscript-included)
- [Command-line (optional)](#command-line-optional)
- [Quality presets](#quality-presets)
- [How it works](#how-it-works)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Features

- Add multiple files or a whole folder
- Choose output folder or save next to source files with a "+-compressed" suffix
- Pick compression level: Strong, Balanced, or High Quality
- Engine selection: Auto (prefers Ghostscript), Ghostscript, or Basic
- Progress bar and live log

## Requirements

- Python 3.9+
- pip to install dependencies
- Optional but recommended: Ghostscript for best compression
  - Windows download: https://ghostscript.com/releases/gsdnld.html

## Setup

1) Create and activate a virtual environment (optional but recommended)

```powershell
# from the project root
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install Python dependencies

```powershell
pip install -r requirements.txt
```

3) Ghostscript installation
- The app will attempt to auto-install Ghostscript on first launch of the GUI (Windows).
- If you prefer manual install, download the Windows installer: https://ghostscript.com/releases/gsdnld.html
- After installation, reopen PowerShell so `gswin64c` is on PATH, or restart the app.

## Run the GUI

```powershell
python -m app
```

## Make a Windows EXE (optional)

You can build a single-file EXE with PyInstaller. By default it won’t include Ghostscript; the app will auto-install it on first run if needed. If you want to bundle Ghostscript portable files, see the bundling notes below.

```powershell
# from project root
.\.venv\Scripts\Activate.ps1
pip install pyinstaller

# Build EXE (no Ghostscript bundled; auto-install on first run)
pwsh package\build_exe.ps1

# Optionally bundle Ghostscript portable files (AGPL obligations apply)
# 1) Put Ghostscript under vendor\ghostscript (bin\gswin64c.exe, etc.)
# 2) Then run:
pwsh package\build_exe.ps1 -BundleGhostscript
```

More details: `package/README-bundling.md`.

## Make a portable ZIP with Ghostscript included

This builds a ZIP containing `PDFKompressor.exe` and a `ghostscript/` folder copied from your system installation.

```powershell
# Ensure Ghostscript is installed (Windows Programs) and EXE is built in dist/
pwsh package\build_portable_zip.ps1
# Produces: dist\PDFKompressor-portable.zip
```

Unzip and run `PDFKompressor.exe`. The app will use the `ghostscript/bin/gswin64c.exe` bundled next to it.

## Command-line (optional)

You can also compress from the terminal (single file or a folder):

```powershell
# Single file (auto engine, balanced quality). Auto-install Ghostscript if missing:
python -m app --input "C:\path\to\file.pdf" --output "C:\path\to\out.pdf" --auto-install-ghostscript

# Folder (compress all PDFs in folder, write to output folder)
python -m app --input "C:\path\to\folder" --output "C:\path\to\out-folder" --quality strong

# Force Ghostscript and auto-install if needed
python -m app --input file.pdf --engine ghostscript --auto-install-ghostscript
python -m app --input file.pdf --engine basic
```

Quality presets:
- extreme → smallest files (very aggressive downsampling and JPEG compression; requires Ghostscript for full effect)
- strong → smaller size (aggressive)
- balanced → good compromise
- high → larger size but better visual fidelity

## How it works

- Engines
  - Ghostscript: best compression via image downsampling and font subsetting
  - Basic (pikepdf): pure Python, focuses on stream compression and cleanup
- Ghostscript detection order
  1) Bundled `ghostscript/bin/gswin64c.exe` next to the EXE (portable mode)
  2) PATH (`gswin64c`, `gswin32c`, `gs`)
  3) Typical Windows installs (e.g., `C:\\Program Files\\gs\\gs*\\bin\\...`)
- If Ghostscript is missing, the app can auto-install it (Windows GUI, or CLI with `--auto-install-ghostscript`).
- To avoid permission/locking quirks, Ghostscript writes to a temp file first, then the app moves it to the final path.
- Files are never overwritten silently—a unique name is chosen when needed.

## Troubleshooting

- "Ghostscript not found" in the GUI: install Ghostscript and reopen the app, or choose Engine = Basic.
- If antivirus blocks Ghostscript calls, allow `gswin64c.exe` or run as Administrator.
- Long-running files: leave the app open; the log will update per file. You can cancel by closing the window.

## License

- App: MIT (see [LICENSE](LICENSE))
- Ghostscript: AGPLv3 when redistributed (bundled). If you distribute Ghostscript with your build, include its license and comply with AGPLv3 terms. See `package/README-bundling.md`.

---

Contributions and issues are welcome!
