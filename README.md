# keynote_to_pdf_compress

[![Stars](https://img.shields.io/github/stars/wytbjtu/keynote_to_pdf_compress?style=flat&logo=github)](https://github.com/wytbjtu/keynote_to_pdf_compress/stargazers)
[![Forks](https://img.shields.io/github/forks/wytbjtu/keynote_to_pdf_compress?style=flat&logo=github)](https://github.com/wytbjtu/keynote_to_pdf_compress/network/members)
[![Watchers](https://img.shields.io/github/watchers/wytbjtu/keynote_to_pdf_compress?style=flat&logo=github)](https://github.com/wytbjtu/keynote_to_pdf_compress/watchers)
[![Issues](https://img.shields.io/github/issues/wytbjtu/keynote_to_pdf_compress?style=flat&logo=github)](https://github.com/wytbjtu/keynote_to_pdf_compress/issues)
[![Last commit](https://img.shields.io/github/last-commit/wytbjtu/keynote_to_pdf_compress?style=flat&logo=github)](https://github.com/wytbjtu/keynote_to_pdf_compress/commits)
[![Commit activity](https://img.shields.io/github/commit-activity/m/wytbjtu/keynote_to_pdf_compress?style=flat&logo=github)](https://github.com/wytbjtu/keynote_to_pdf_compress/pulse)
[![Contributors](https://img.shields.io/github/contributors/wytbjtu/keynote_to_pdf_compress?style=flat&logo=github)](https://github.com/wytbjtu/keynote_to_pdf_compress/graphs/contributors)
[![Repo size](https://img.shields.io/github/repo-size/wytbjtu/keynote_to_pdf_compress?style=flat&logo=github)](https://github.com/wytbjtu/keynote_to_pdf_compress)
[![Code size](https://img.shields.io/github/languages/code-size/wytbjtu/keynote_to_pdf_compress?style=flat&logo=github)](https://github.com/wytbjtu/keynote_to_pdf_compress)
[![License](https://img.shields.io/github/license/wytbjtu/keynote_to_pdf_compress?style=flat)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey?style=flat&logo=apple)](https://www.apple.com/macos/)

Export an Apple Keynote (`.key`) presentation to PDF and produce a
compressed copy in one step.

The export is driven by Keynote itself through AppleScript (since the
`.key` format isn't readable by Python libraries), and the compression
pass is done with Ghostscript.

## Requirements

- macOS with [Keynote](https://apps.apple.com/app/keynote/id409183694) installed
- Python 3.9+ (skip if you use the prebuilt binary below)
- [Ghostscript](https://www.ghostscript.com/) on `PATH` (`gs`)

Install Ghostscript with Homebrew:

```sh
brew install ghostscript
```

## Download a prebuilt binary (macOS)

Grab the latest `.zip` for your architecture from the
[Releases page](https://github.com/wytbjtu/keynote_to_pdf_compress/releases):

- Apple Silicon (M1/M2/M3): `keynote_to_pdf_compress-macos-arm64.zip`
- Intel: `keynote_to_pdf_compress-macos-x86_64.zip`

The binary isn't notarized, so the first run is blocked by Gatekeeper.
Either right-click → **Open** → **Open**, or remove the quarantine
attribute once:

```sh
xattr -d com.apple.quarantine ./keynote_to_pdf_compress
```

> Windows is not supported — Keynote and AppleScript are macOS-only, so a
> Windows build of this tool cannot drive the export.

## Usage

```sh
python3 keynote_to_pdf_compress.py path/to/deck.key
```

This produces two files next to the source `.key`:

- `deck.pdf` — uncompressed Keynote export
- `deck_compressed_ebook.pdf` — Ghostscript-compressed copy

### Options

| Flag | Description | Default |
| --- | --- | --- |
| `--pdf PATH` | Path for the uncompressed PDF | `<deck>.pdf` |
| `--compressed PATH` | Path for the compressed PDF | `<deck>_compressed_<preset>.pdf` |
| `--quality {Good,Better,Best}` | Image quality used by Keynote during export | `Better` |
| `--preset {screen,ebook,printer,prepress,default}` | Ghostscript `-dPDFSETTINGS` preset | `ebook` |
| `--image-dpi N` | Target DPI for color/gray images when compressing | `180` |
| `--compress-only` | Skip the Keynote step and compress the existing `--pdf` file | off |
| `--remove-source-pdf` | Delete the uncompressed PDF after compression | off |

### Examples

Export with the highest Keynote quality, then compress aggressively for
screen viewing:

```sh
python3 keynote_to_pdf_compress.py deck.key \
    --quality Best --preset screen --image-dpi 120
```

Re-compress a PDF you already have:

```sh
python3 keynote_to_pdf_compress.py deck.key \
    --compress-only --pdf deck.pdf --compressed deck_small.pdf
```

Export, compress, and discard the large intermediate PDF:

```sh
python3 keynote_to_pdf_compress.py deck.key --remove-source-pdf
```

## Preset cheatsheet

Ghostscript's presets trade size for fidelity:

- `screen` — smallest, ~72 dpi images, good for email/web
- `ebook` — small, ~150 dpi images, good default for sharing
- `printer` — ~300 dpi images, good for office printing
- `prepress` — ~300 dpi, preserves color, for commercial printing
- `default` — Ghostscript's general-purpose settings

Explicit `--image-dpi` overrides the color/gray image resolution from the
preset.

## Notes

- The script launches Keynote, opens the file, exports it, then closes
  the opened document. Keynote itself is left running.
- Exports can take a while; the AppleScript timeout is 30 minutes per
  document.
- Exit status is `0` on success, `1` on any handled error (file missing,
  Ghostscript missing, Keynote/Ghostscript failure, etc.).

## License

MIT — see [LICENSE](LICENSE).
