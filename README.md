# Ren'Py Asset Extraction Tool v2.0

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![UI Framework](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-brightgreen.svg)](https://www.qt.io/qt-for-python)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Good First Issues](https://img.shields.io/badge/contributions-good%20first%20issues-orange.svg)](https://github.com/abhishek-s12/rpa-extractor/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
[![Continuous Integration](https://github.com/abhishek-s12/rpa-extractor/actions/workflows/ci.yml/badge.svg)](https://github.com/abhishek-s12/rpa-extractor/actions/workflows/ci.yml)

A professional-grade PySide6 (Qt6) desktop application and command-line utility built in Python to scan, inspect, preview, unpack, decompile, and repack Ren'Py game assets and `.rpa` archives.

Designed for digital preservation, modding, localization, and educational backup of assets from games that you legally own.

---

## ✨ Features in v2.0

- 🎨 **PySide6 (Qt6) Desktop Interface**: Responsive splitter layout, dark theme accents, glassmorphic card widgets, and custom font support.
- 🎵 **Interactive Audio Player**: Waveform visualization canvas with **click-to-seek** playback position and audio controls.
- 🎬 **Real-Time Video HUD**: Dynamic overlay displaying video resolution, framerate, and time index live on video frames during playback.
- 🖼️ **Image Inspector**: Zoom-to-cursor, pan, reset controls, and a **side-by-side comparison slider** for original vs optimized images.
- 📦 **RPA Archive Compiler (Repacker)**: Package customized asset folders into encrypted/obfuscated Ren'Py Archive (`.rpa` v3/v2) files with custom XOR key support.
- 📜 **Built-in `.rpyc` Decompiler**: Reverse compile Ren'Py compiled scripts (`.rpyc`) back into editable `.rpy` scripts with in-app **syntax highlighting**.
- 🔍 **Smart Search & Filter HUD**: Query assets by dimensions (`width >= 1080`), duration (`duration > 60`), size (`size > 2MB`), category (`cat:audio`), or regex (`re:^bg_.*`) with preset management.
- ⚡ **Fast Mode & Manifest Catalog**: Unpack archives in under 1-2 minutes or generate a full `metadata.json` catalog with file checksums.

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10+

### Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/abhishek-s12/rpa-extractor.git
   cd rpa-extractor
   ```

2. **Set up Virtual Environment**:
   ```bash
   # Create virtual environment
   python -m venv .venv

   # Activate environment
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # macOS / Linux:
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the PySide6 Application**:
   ```bash
   python main.py gui
   # Or simply:
   python main.py
   ```

---

## 💻 Command Line Interface (CLI)

- **Scan a game folder or archive**:
  ```bash
  python main.py scan /path/to/game
  ```
- **Extract specific asset categories**:
  ```bash
  python main.py extract /path/to/game -o /path/to/output --category audio --category images --fast
  ```
- **Repack a folder into a `.rpa` archive**:
  ```bash
  python main.py repack /path/to/folder -o /path/to/output.rpa --version RPA-3.0 --key 0424b2b4
  ```
- **Decompile `.rpyc` script files**:
  ```bash
  python main.py decompile /path/to/script.rpyc -o /path/to/output_folder
  ```

---

## 🧪 Testing

Run the automated `pytest` test suite:
```bash
python -m pytest
```

---

## 🤝 Contributing

We welcome contributions! Check out our open **[Good First Issues](https://github.com/abhishek-s12/rpa-extractor/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)** for beginner-friendly tasks.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for full development environment setup and pull request guidelines.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
