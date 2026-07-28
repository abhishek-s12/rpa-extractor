# Ren'Py Asset Extraction Tool

A professional-grade desktop application and command-line utility built from scratch in Python to scan, inspect, preview, and selectively unpack Ren'Py game directories and `.rpa` archives.

This tool is designed for digital preservation, modding, localization, and educational backup of assets from games that you legally own.

## Features

- **Game Folder Detection**: Automatically identifies standard Ren'Py game folders, scripts, and archives.
- **Hierarchical Asset Tree**: Lists both loose file directories and internal `.rpa` archive structures before extraction.
- **Rich Media Preview**: In-app image preview (Pillow), audio specifications (Mutagen), video characteristics (OpenCV), and script line metrics (dialogues, labels, definitions).
- **Filters & Selective Unpacking**: Extract everything, or selectively extract specific types of files:
  - Audio files only (`.mp3`, `.ogg`, `.wav`, etc.)
  - Images only (`.png`, `.jpg`, `.webp`, etc.)
  - Video files only (`.mp4`, `.webm`, etc.)
  - Scripts only (`.rpy`, `.rpyc`)
  - Fonts and Game data files
- **Background Multi-threading**: Background scanner and extractors keep the GUI responsive during heavy tasks, displaying speeds and ETAs.
- **Manifest Catalog**: Automatically generates a `metadata.json` mapping of all extracted files with file sizes, relative paths, MD5/SHA256 checksums, and image perceptual hashes.

## Project Structure

```
renpy-extractor/
├── app/                  # Main GUI modules
├── core/                 # Scanners, archive readers, and configuration utilities
├── extractors/           # Audio, video, and image specifications extraction
├── parsers/              # Ren'Py script scanning and metrics
├── ui/                   # CustomTkinter interface frames, previews, and styles
├── workers/              # Background threads handling scan and extraction
├── tests/                # Unit test suite verifying binary unpickling
├── main.py               # Launcher entrypoint supporting CLI and GUI
└── pyproject.toml        # Ruff/mypy formatting and linter configurations
```

## Setup & Run

### Prerequisites
- Python 3.11+
- Standard Tk/Tcl libraries (usually bundled with Python)

### Installation
1. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```
2. Install dependency packages:
   ```bash
   pip install -r requirements.txt
   ```

### Execution

#### Headless CLI
- Scan a game folder or individual archive:
  ```bash
  python main.py scan /path/to/game
  ```
- Extract specific categories (e.g., audio and images only) using high-speed **Fast Mode** (skips calculating hashes/media specs):
  ```bash
  python main.py extract /path/to/game --output /path/to/output --category audio --category images --fast
  ```
  *(Omit the `--fast` or `-f` flag if you want to generate full MD5/SHA256 checksums and Pillow/Mutagen/OpenCV property sheets in `metadata.json`)*

#### Graphical Desktop App
- Launch the GUI:
  ```bash
  python main.py gui
  # Or simply run without arguments
  python main.py
  ```
  *In the sidebar, check the **Fast Mode (Skip Metadata)** option to skip heavy analysis and perform a direct concurrent file copy (recommended for unpacking games in under 1-2 minutes).*

## Testing
Run the pytest suite to verify archive decryption and file category classification rules:
```bash
python -m pytest
```

## Standalone Executable Build (Windows)

To compile the standalone `RenPyExtractor.exe` executable yourself:
1. Activate the virtual environment and ensure dependencies (including PyInstaller) are installed.
2. Run the build compiler script:
   ```bash
   python build_exe.py
   ```
This will compile, bundle all customtkinter theme configurations/assets, and write the output `RenPyExtractor.exe` file inside the `dist/` directory.

Users can download the pre-compiled, double-clickable `RenPyExtractor.exe` binary directly from the [GitHub Releases](https://github.com/abhishek-s12/rpa-extractor/releases) page.

