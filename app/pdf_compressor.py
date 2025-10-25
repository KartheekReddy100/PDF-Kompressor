from __future__ import annotations

import os
import subprocess
import tempfile
import shutil
from dataclasses import dataclass
from typing import Literal, Optional, Tuple

# Lazy imports inside functions for optional deps

Quality = Literal["extreme", "strong", "balanced", "high"]
Engine = Literal["auto", "ghostscript", "basic"]


@dataclass
class CompressResult:
    ok: bool
    engine: Engine
    input_path: str
    output_path: str
    message: str = ""


def _map_quality_to_pdfsettings(quality: Quality) -> str:
    # Ghostscript presets
    # /screen (strong), /ebook (balanced), /printer (high)
    return {
        "extreme": "screen",
        "strong": "screen",
        "balanced": "ebook",
        "high": "printer",
    }[quality]


def _ghostscript_extra_args_for_quality(quality: Quality) -> list[str]:
    """Additional Ghostscript tuning per quality level.

    For 'extreme', we aggressively downsample and lower JPEG quality.
    For other presets, rely mostly on -dPDFSETTINGS with minimal tweaks.
    """
    if quality == "extreme":
        return [
            # Downsample color/gray images to 72 DPI using average downsampling
            "-dDownsampleColorImages=true",
            "-dColorImageDownsampleType=/Average",
            "-dColorImageResolution=72",
            "-dDownsampleGrayImages=true",
            "-dGrayImageDownsampleType=/Average",
            "-dGrayImageResolution=72",
            # For mono images, subsample to keep it small
            "-dDownsampleMonoImages=true",
            "-dMonoImageDownsampleType=/Subsample",
            "-dMonoImageResolution=150",
            # Force JPEG for color/gray with low quality factor
            "-dAutoFilterColorImages=false",
            "-dColorImageFilter=/DCTEncode",
            "-dAutoFilterGrayImages=false",
            "-dGrayImageFilter=/DCTEncode",
            "-dJPEGQ=20",
            # Misc size savers
            "-dDetectDuplicateImages=true",
            "-dSubsetFonts=true",
            "-dCompressFonts=true",
        ]
    elif quality == "strong":
        return [
            "-dDownsampleColorImages=true",
            "-dColorImageDownsampleType=/Average",
            "-dColorImageResolution=96",
            "-dDownsampleGrayImages=true",
            "-dGrayImageDownsampleType=/Average",
            "-dGrayImageResolution=96",
            "-dDownsampleMonoImages=true",
            "-dMonoImageDownsampleType=/Subsample",
            "-dMonoImageResolution=180",
            "-dAutoFilterColorImages=false",
            "-dColorImageFilter=/DCTEncode",
            "-dAutoFilterGrayImages=false",
            "-dGrayImageFilter=/DCTEncode",
            "-dJPEGQ=35",
            "-dDetectDuplicateImages=true",
            "-dSubsetFonts=true",
            "-dCompressFonts=true",
        ]
    else:
        # Balanced/High: use Ghostscript defaults for the preset; keep duplicate image detection
        return [
            "-dDetectDuplicateImages=true",
            "-dSubsetFonts=true",
            "-dCompressFonts=true",
        ]


def compress_with_ghostscript(
    input_path: str,
    output_path: str,
    quality: Quality = "balanced",
    gs_path: Optional[str] = None,
    timeout: Optional[int] = None,
) -> CompressResult:
    from .ghostscript_finder import get_ghostscript_path

    if gs_path is None:
        gs_path = get_ghostscript_path()
    if not gs_path or not os.path.exists(gs_path):
        return CompressResult(False, "ghostscript", input_path, output_path, "Ghostscript not found")

    pdfsettings = _map_quality_to_pdfsettings(quality)

    # Build command
    # Write to a temp file first to avoid device/path quirks, then move to target
    tmp_fd, tmp_out = tempfile.mkstemp(suffix=".pdf")
    os.close(tmp_fd)

    cmd = [
        gs_path,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS=/{pdfsettings}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={tmp_out}",
        input_path,
    ]

    # Inject extra args for tuning
    extra = _ghostscript_extra_args_for_quality(quality)
    cmd[5:5] = extra  # place extras before control flags/output

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if proc.returncode == 0 and os.path.exists(tmp_out):
            # Ensure target directory exists
            try:
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            except Exception:
                pass
            try:
                # Move temp output to requested destination
                if os.path.exists(output_path):
                    os.remove(output_path)
                shutil.move(tmp_out, output_path)
            except Exception as move_err:
                # If move failed, keep temp file and report
                return CompressResult(False, "ghostscript", input_path, output_path, f"Move failed: {move_err}")
            return CompressResult(True, "ghostscript", input_path, output_path, "Compressed with Ghostscript")
        else:
            msg = proc.stderr.strip() or proc.stdout.strip() or f"Exited with code {proc.returncode}"
            return CompressResult(False, "ghostscript", input_path, output_path, msg)
    except subprocess.TimeoutExpired:
        return CompressResult(False, "ghostscript", input_path, output_path, "Ghostscript timed out")
    except Exception as e:
        return CompressResult(False, "ghostscript", input_path, output_path, f"Ghostscript error: {e}")
    finally:
        try:
            if os.path.exists(tmp_out):
                os.remove(tmp_out)
        except Exception:
            pass


def compress_with_pikepdf(
    input_path: str,
    output_path: str,
    quality: Quality = "balanced",
) -> CompressResult:
    """
    Basic compression using pikepdf / qpdf optimizations. This primarily compresses streams
    and removes unused objects. It usually won't re-encode images aggressively but still
    yields a meaningful size reduction with no external tools.
    """
    try:
        import pikepdf  # type: ignore
    except Exception as e:
        return CompressResult(False, "basic", input_path, output_path, f"pikepdf not available: {e}")

    try:
        with pikepdf.open(input_path) as pdf:
            # Aggressive stream compression and linearization; keep PDF/A if possible off for better compression
            pdf.save(
                output_path,
                compress_streams=True,
                # object_stream_mode is available across pikepdf versions; fall back if enum not present
                # linearization makes web loading faster and may slightly alter structure
                linearize=True,
            )
        if os.path.exists(output_path):
            return CompressResult(True, "basic", input_path, output_path, "Compressed with pikepdf")
        else:
            return CompressResult(False, "basic", input_path, output_path, "Unknown error during save")
    except Exception as e:
        return CompressResult(False, "basic", input_path, output_path, f"pikepdf error: {e}")


def auto_compress(
    input_path: str,
    output_path: str,
    quality: Quality = "balanced",
) -> CompressResult:
    from .ghostscript_finder import get_ghostscript_path

    gs = get_ghostscript_path()
    if gs:
        res = compress_with_ghostscript(input_path, output_path, quality, gs_path=gs)
        if res.ok:
            return res
        # if GS failed, fall back
    return compress_with_pikepdf(input_path, output_path, quality)


def choose_engine(engine: Engine):
    if engine == "ghostscript":
        return compress_with_ghostscript
    if engine == "basic":
        return compress_with_pikepdf
    return auto_compress


def ensure_unique_output_path(base_path: str) -> str:
    """Return a non-clobbering path appending (1), (2), ... if needed."""
    if not os.path.exists(base_path):
        return base_path
    root, ext = os.path.splitext(base_path)
    i = 1
    while True:
        candidate = f"{root} ({i}){ext}"
        if not os.path.exists(candidate):
            return candidate
        i += 1


def default_output_path_for(src_path: str, output_dir: Optional[str]) -> str:
    name = os.path.basename(src_path)
    stem, _ = os.path.splitext(name)
    target_dir = output_dir or os.path.dirname(src_path)
    out = os.path.join(target_dir, f"{stem}-compressed.pdf")
    return ensure_unique_output_path(out)
