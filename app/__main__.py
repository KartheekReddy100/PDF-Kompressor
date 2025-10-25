import argparse
import os
import sys

# Ensure parent directory is importable when run as a script (no package context)
if __package__ in (None, ""):
    try:
        _here = os.path.dirname(os.path.abspath(__file__))
        _parent = os.path.abspath(os.path.join(_here, os.pardir))
        if _parent not in sys.path:
            sys.path.insert(0, _parent)
    except Exception:
        pass

# Support both package (python -m app) and script/pyinstaller execution
try:
    from .ghostscript_installer import ensure_ghostscript_installed
    from .pdf_compressor import (
        Engine,
        Quality,
        auto_compress,
        choose_engine,
        default_output_path_for,
    )
    from .logging_utils import safe_log
except Exception:
    from app.ghostscript_installer import ensure_ghostscript_installed
    from app.pdf_compressor import (
        Engine,
        Quality,
        auto_compress,
        choose_engine,
        default_output_path_for,
    )
    from app.logging_utils import safe_log


def _run_cli() -> int:
    parser = argparse.ArgumentParser(
        description="PDF Compressor (GUI or CLI)",
        epilog="If no arguments are provided, the GUI will launch.",
    )
    parser.add_argument("--input", "-i", help="Input PDF file or folder of PDFs")
    parser.add_argument("--output", "-o", help="Output file or folder (optional)")
    parser.add_argument(
        "--engine",
        choices=["auto", "ghostscript", "basic"],
        default="auto",
        help="Compression engine",
    )
    parser.add_argument(
        "--auto-install-ghostscript",
        action="store_true",
        help="When Ghostscript is missing, attempt to download and install it automatically before running",
    )
    parser.add_argument(
        "--quality",
        choices=["extreme", "strong", "balanced", "high"],
        default="balanced",
        help="Compression quality preset",
    )

    args = parser.parse_args()

    if not args.input:
        # Launch GUI; auto-install Ghostscript to maximize compression experience
        try:
            ensure_ghostscript_installed(auto_install=True)
        except Exception as e:
            safe_log(f"Auto-install ghostscript failed: {e}")
        try:
            # Lazy import GUI so we can catch import errors and report
            try:
                from .gui import main as gui_main
            except Exception:
                from app.gui import main as gui_main
        except Exception as e:
            _log = safe_log(f"GUI import failed: {e}")
            _show_critical_message(
                "Startup error",
                f"Could not start the GUI. See log for details.\nLog: {_log or 'unavailable'}",
            )
            return 2
        try:
            gui_main()
        except Exception as e:
            _log = safe_log(f"GUI runtime error: {e}")
            _show_critical_message(
                "Runtime error",
                f"An error occurred. See log for details.\nLog: {_log or 'unavailable'}",
            )
            return 2
        return 0

    in_path = os.path.abspath(args.input)
    out_arg = os.path.abspath(args.output) if args.output else None
    engine: Engine = args.engine  # type: ignore
    quality: Quality = args.quality  # type: ignore

    compressor = choose_engine(engine)

    # Optional auto-install for CLI paths
    if args.auto_install_ghostscript and engine in ("ghostscript", "auto"):
        try:
            ensure_ghostscript_installed(auto_install=True)
        except Exception:
            pass

    def compress_one(src: str, out_dir: str | None) -> tuple[str, bool, str]:
        out_path = (
            out_arg
            if out_arg and os.path.splitext(out_arg)[1].lower() == ".pdf"
            else default_output_path_for(src, out_dir)
        )
        res = compressor(src, out_path, quality)  # type: ignore[arg-type]
        return (out_path, res.ok, res.message)

    if os.path.isdir(in_path):
        # Folder mode
        out_dir = out_arg if (out_arg and os.path.isdir(out_arg)) else out_arg
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        pdfs = [
            os.path.join(in_path, f)
            for f in os.listdir(in_path)
            if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(in_path, f))
        ]
        if not pdfs:
            print("No PDF files found in folder.")
            return 1

        ok_count = 0
        for i, p in enumerate(pdfs, start=1):
            out_path, ok, msg = compress_one(p, out_dir)
            status = "OK" if ok else "FAIL"
            print(f"[{i}/{len(pdfs)}] {status}: {os.path.basename(p)} -> {out_path}")
            if not ok:
                print(f"   {msg}")
            else:
                ok_count += 1
        print(f"Done. {ok_count}/{len(pdfs)} succeeded.")
        return 0 if ok_count == len(pdfs) else 2
    else:
        # Single file
        if not in_path.lower().endswith(".pdf") or not os.path.exists(in_path):
            print("Input must be an existing PDF file or a folder.")
            return 1
        out_dir = None if (out_arg and os.path.splitext(out_arg)[1].lower() == ".pdf") else out_arg
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        out_path, ok, msg = compress_one(in_path, out_dir)
        if ok:
            print(f"OK: {os.path.basename(in_path)} -> {out_path}")
            return 0
        else:
            print(f"FAIL: {msg}")
            return 2


if __name__ == "__main__":
    def _show_critical_message(title: str, text: str) -> None:
        try:
            import ctypes

            MB_OK = 0x0
            MB_ICONERROR = 0x10
            ctypes.windll.user32.MessageBoxW(None, text, title, MB_OK | MB_ICONERROR)
        except Exception:
            # Last resort: print to stderr (helpful when run from console)
            try:
                sys.stderr.write(f"{title}: {text}\n")
            except Exception:
                pass

    sys.exit(_run_cli())
