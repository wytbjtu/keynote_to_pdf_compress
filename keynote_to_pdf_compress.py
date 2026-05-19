#!/usr/bin/env python3
"""Export a Keynote file to PDF and create a compressed copy.

The script uses AppleScript through ``osascript`` because Apple's Keynote file
format is not directly exportable by Python libraries. Ghostscript is used for
the compression pass.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


DEFAULT_KEYNOTE = Path(
    "/Users/laoowai/Documents/MacSD/wife/260518 keynote/Alyson 2.key"
)


def run_command(command: list[str], *, timeout: int | None = None) -> None:
    """Run a subprocess and raise a helpful error if it fails."""
    try:
        subprocess.run(command, check=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required command not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        joined = " ".join(command)
        raise RuntimeError(f"Command failed with exit code {exc.returncode}: {joined}") from exc


def export_keynote_to_pdf(keynote_path: Path, pdf_path: Path) -> None:
    """Export a Keynote presentation to PDF using Keynote via AppleScript."""
    if not keynote_path.exists():
        raise FileNotFoundError(f"Keynote file does not exist: {keynote_path}")

    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    applescript = f"""
set keynoteFile to POSIX file "{keynote_path}" as alias
set pdfFile to POSIX file "{pdf_path}"

tell application "Keynote"
    launch
    activate
end tell
delay 2

tell application "Keynote"
    open keynoteFile
    delay 3
    with timeout of 1800 seconds
        export front document to pdfFile as PDF with properties {{PDF image quality:Better}}
    end timeout
end tell
"""
    run_command(["osascript", "-e", applescript], timeout=1900)

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise RuntimeError(f"Keynote export did not create a valid PDF: {pdf_path}")

    close_script = 'tell application "Keynote" to close every document saving no'
    subprocess.run(["osascript", "-e", close_script], check=False, timeout=60)


def compress_pdf(input_pdf: Path, output_pdf: Path) -> None:
    """Compress a PDF with medium settings while keeping readable quality."""
    if not input_pdf.exists():
        raise FileNotFoundError(f"PDF file does not exist: {input_pdf}")

    ghostscript = shutil.which("gs")
    if ghostscript is None:
        raise RuntimeError("Ghostscript was not found. Install it or add `gs` to PATH.")

    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    command = [
        ghostscript,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.5",
        "-dPDFSETTINGS=/ebook",
        "-dColorImageResolution=180",
        "-dGrayImageResolution=180",
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


def default_pdf_paths(keynote_path: Path) -> tuple[Path, Path]:
    """Return uncompressed and compressed output paths for a Keynote file."""
    exported_pdf = keynote_path.with_suffix(".pdf")
    compressed_pdf = keynote_path.with_name(f"{keynote_path.stem}_compressed_medium.pdf")
    return exported_pdf, compressed_pdf


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Export a .key presentation to PDF and compress it."
    )
    parser.add_argument(
        "keynote",
        nargs="?",
        type=Path,
        default=DEFAULT_KEYNOTE,
        help=f"Keynote file to export. Default: {DEFAULT_KEYNOTE}",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        help="Optional path for the uncompressed exported PDF.",
    )
    parser.add_argument(
        "--compressed",
        type=Path,
        help="Optional path for the compressed PDF.",
    )
    parser.add_argument(
        "--compress-only",
        action="store_true",
        help="Skip Keynote export and compress the existing --pdf file.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the Keynote export and PDF compression workflow."""
    args = parse_args()
    keynote_path = args.keynote.expanduser().resolve()
    default_pdf, default_compressed = default_pdf_paths(keynote_path)
    pdf_path = (args.pdf or default_pdf).expanduser().resolve()
    compressed_path = (args.compressed or default_compressed).expanduser().resolve()

    if args.compress_only:
        print(f"Compressing existing PDF: {pdf_path}", flush=True)
    else:
        print(f"Exporting Keynote to PDF: {keynote_path}", flush=True)
        export_keynote_to_pdf(keynote_path, pdf_path)

    print(f"Creating compressed PDF: {compressed_path}", flush=True)
    compress_pdf(pdf_path, compressed_path)

    source_size = pdf_path.stat().st_size / (1024 * 1024)
    compressed_size = compressed_path.stat().st_size / (1024 * 1024)
    print(f"Exported PDF: {pdf_path} ({source_size:.1f} MB)", flush=True)
    print(f"Compressed PDF: {compressed_path} ({compressed_size:.1f} MB)", flush=True)


if __name__ == "__main__":
    main()
