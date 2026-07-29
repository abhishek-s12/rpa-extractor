# Contributing to Ren'Py Asset Extraction Tool

Thank you for your interest in contributing to the **Ren'Py Asset Extraction Tool**! We welcome all contributions—whether it's fixing bugs, adding media previewers, enhancing PySide6 UI components, or improving documentation.

---

## 🌟 Finding a Good First Issue

If you are new to open source or to this codebase, look for issues labeled with **`good first issue`**:

👉 **[Browse Good First Issues](https://github.com/abhishek-s12/rpa-extractor/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)**

These issues are beginner-friendly, well-scoped, and include hints to help you get started quickly!

---

## 🛠️ Local Development Setup

### 1. Fork and Clone the Repository

1. Fork the repo on GitHub by clicking the **Fork** button.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/rpa-extractor.git
   cd rpa-extractor
   ```

### 2. Create a Virtual Environment

Set up a clean Python virtual environment (`.venv`):

```bash
# Create environment
python -m venv .venv

# Activate environment:
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Windows (CMD):
.venv\Scripts\activate.bat
# On macOS / Linux:
source .venv/bin/activate
```

### 3. Install Dependencies

Install all development and UI dependencies:

```bash
pip install -r requirements.txt
```

---

## 🧪 Running Tests & Application

### Run Automated Unit Tests

Before making any changes, verify that the existing test suite passes:

```bash
python -m pytest
```

### Run PySide6 Application

Launch the desktop GUI locally to test your changes:

```bash
python main.py gui
```

---

## 📁 Project Structure Overview

- **`core/`**: RPA archive detector, reader (`RpaArchiveReader`), repacker (`RpaArchiveWriter`), smart filter query engine, and settings.
- **`parsers/`**: Ren'Py script parser & `.rpyc` decompiler (`RpycDecompiler`).
- **`ui/`**: PySide6 application window (`app_qt.py`), theme (`theme.py`), and syntax highlighter.
- **`ui/widgets/`**: Reusable Qt widgets (`audio_player.py`, `video_player.py`, `image_inspector.py`, `repacker_tab.py`, `decompiler_tab.py`, `filter_hud.py`).
- **`tests/`**: PyTest unit tests.

---

## 📋 Code Style & Formatting

- Follow **PEP 8** coding standards.
- Add type hints (`from typing import ...`) for function arguments and return types.
- Ensure all new widgets subclass PySide6 Qt classes cleanly.
- Run `pytest` to make sure all tests continue to pass.

---

## 🚀 Submitting a Pull Request (PR)

1. **Create a new branch** for your feature or bugfix:
   ```bash
   git checkout -b feat/keyboard-shortcuts
   ```
2. **Commit your changes** with a clear commit message:
   ```bash
   git commit -m "feat(ui): Add Spacebar and Arrow key shortcuts to media players"
   ```
3. **Push to your fork**:
   ```bash
   git push origin feat/keyboard-shortcuts
   ```
4. **Open a Pull Request**:
   - Go to the main repository `https://github.com/abhishek-s12/rpa-extractor`.
   - Click **New Pull Request** and select your branch.
   - Describe your changes and link the issue number (e.g., `Closes #1`).

Thank you for helping make the Ren'Py Asset Extraction Tool better! 🎉
