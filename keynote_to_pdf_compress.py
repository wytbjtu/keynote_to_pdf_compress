#!/usr/bin/env python3
"""Export a Keynote presentation to PDF and produce a compressed copy.

Keynote's ``.key`` format is not readable by Python libraries, so the export
step drives Keynote itself via AppleScript (``osascript``). The compression
step uses Ghostscript (``gs``).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


# Ghostscript ``-dPDFSETTINGS`` presets, ordered from smallest/lowest quality
# to largest/highest quality.
PDF_PRESETS = ("screen", "ebook", "printer", "prepress", "default")

# Keynote export image quality values understood by AppleScript.
KEYNOTE_QUALITIES = ("Good", "Better", "Best")


def run_command(command: list[str], *, timeout: int | None = None) -> None:
    """Run a subprocess and raise a helpful error if it fails."""
    try:
        subprocess.run(command, check=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required command not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        joined = " ".join(command)
        raise RuntimeError(
            f"Command failed with exit code {exc.returncode}: {joined}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Command timed out after {exc.timeout}s: {command[0]}") from exc


def _applescript_quote(value: str) -> str:
    """Escape a string for safe interpolation inside an AppleScript literal."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def export_keynote_to_pdf(
    keynote_path: Path,
    pdf_path: Path,
    *,
    quality: str = "Better",
) -> None:
    """Export a Keynote presentation to PDF using Keynote via AppleScript."""
    if sys.platform != "darwin":
        raise RuntimeError("Keynote export is only supported on macOS.")
    if not keynote_path.exists():
        raise FileNotFoundError(f"Keynote file does not exist: {keynote_path}")
    if quality not in KEYNOTE_QUALITIES:
        raise ValueError(
            f"Unknown Keynote quality '{quality}'. Choose one of: {', '.join(KEYNOTE_QUALITIES)}"
        )

    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    key_literal = _applescript_quote(str(keynote_path))
    pdf_literal = _applescript_quote(str(pdf_path))

    applescript = f"""
set keynoteFile to POSIX file "{key_literal}" as alias
set pdfFile to POSIX file "{pdf_literal}"

tell application "Keynote"
    activate
    set theDoc to open keynoteFile
    with timeout of 1800 seconds
        export theDoc to pdfFile as PDF with properties {{PDF image quality:{quality}}}
    end timeout
    close theDoc saving no
end tell
"""
    run_command(["osascript", "-e", applescript], timeout=1900)

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise RuntimeError(f"Keynote export did not create a valid PDF: {pdf_path}")


def compress_pdf(
    input_pdf: Path,
    output_pdf: Path,
    *,
    preset: str = "ebook",
    image_dpi: int = 180,
) -> None:
    """Compress a PDF with Ghostscript while keeping readable image quality."""
    if not input_pdf.exists():
        raise FileNotFoundError(f"PDF file does not exist: {input_pdf}")
    if preset not in PDF_PRESETS:
        raise ValueError(
            f"Unknown preset '{preset}'. Choose one of: {', '.join(PDF_PRESETS)}"
        )

    ghostscript = shutil.which("gs")
    if ghostscript is None:
        raise RuntimeError(
            "Ghostscript was not found. Install it (e.g. `brew install ghostscript`) "
            "or add `gs` to PATH."
        )

    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    command = [
        ghostscript,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.5",
        f"-dPDFSETTINGS=/{preset}",
        f"-dColorImageResolution={image_dpi}",
        f"-dGrayImageResolution={image_dpi}",
        "-dMonoImageResolution=300",
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",
        "-dSubsetFonts=true",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_pdf}",
        str(input_pdf),
    ]
    run_command(command)

    if not output_pdf.exists() or output_pdf.stat().st_size == 0:
        raise RuntimeError(f"Ghostscript did not produce a valid PDF: {output_pdf}")


def default_pdf_paths(keynote_path: Path, preset: str) -> tuple[Path, Path]:
    """Return uncompressed and compressed output paths for a Keynote file."""
    exported_pdf = keynote_path.with_suffix(".pdf")
    compressed_pdf = keynote_path.with_name(
        f"{keynote_path.stem}_compressed_{preset}.pdf"
    )
    return exported_pdf, compressed_pdf


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Export a Keynote (.key) presentation to PDF and compress it with "
            "Ghostscript."
        )
    )
    parser.add_argument(
        "keynote",
        type=Path,
        help="Path to the Keynote (.key) file to export.",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        help="Path for the uncompressed exported PDF (default: alongside the .key file).",
    )
    parser.add_argument(
        "--compressed",
        type=Path,
        help="Path for the compressed PDF (default: alongside the .key file).",
    )
    parser.add_argument(
        "--quality",
        choices=KEYNOTE_QUALITIES,
        default="Better",
        help="Image quality used by Keynote when exporting (default: Better).",
    )
    parser.add_argument(
        "--preset",
        choices=PDF_PRESETS,
        default="ebook",
        help="Ghostscript -dPDFSETTINGS preset (default: ebook).",
    )
    parser.add_argument(
        "--image-dpi",
        type=int,
        default=180,
        help="Target DPI for color/gray images when compressing (default: 180).",
    )
    parser.add_argument(
        "--compress-only",
        action="store_true",
        help="Skip Keynote export and only compress the existing --pdf file.",
    )
    parser.add_argument(
        "--remove-source-pdf",
        action="store_true",
        help="Delete the uncompressed PDF after compression succeeds.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the Keynote export and PDF compression workflow."""
    args = parse_args(argv)
    keynote_path = args.keynote.expanduser().resolve()
    default_pdf, default_compressed = default_pdf_paths(keynote_path, args.preset)
    pdf_path = (args.pdf or default_pdf).expanduser().resolve()
    compressed_path = (args.compressed or default_compressed).expanduser().resolve()

    if pdf_path == compressed_path:
        raise SystemExit("--pdf and --compressed must point to different files.")

    try:
        if args.compress_only:
            print(f"Compressing existing PDF: {pdf_path}", flush=True)
        else:
            print(f"Exporting Keynote to PDF: {keynote_path}", flush=True)
            export_keynote_to_pdf(keynote_path, pdf_path, quality=args.quality)

        print(
            f"Creating compressed PDF (preset={args.preset}, dpi={args.image_dpi}): "
            f"{compressed_path}",
            flush=True,
        )
        compress_pdf(
            pdf_path,
            compressed_path,
            preset=args.preset,
            image_dpi=args.image_dpi,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr, flush=True)
        return 1

    source_size = pdf_path.stat().st_size / (1024 * 1024)
    compressed_size = compressed_path.stat().st_size / (1024 * 1024)
    ratio = (compressed_size / source_size) if source_size else 0.0
    print(f"Exported PDF:   {pdf_path} ({source_size:.1f} MB)", flush=True)
    print(
        f"Compressed PDF: {compressed_path} ({compressed_size:.1f} MB, "
        f"{ratio * 100:.0f}% of original)",
        flush=True,
    )

    if args.remove_source_pdf and not args.compress_only and pdf_path != compressed_path:
        pdf_path.unlink(missing_ok=True)
        print(f"Removed uncompressed PDF: {pdf_path}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
