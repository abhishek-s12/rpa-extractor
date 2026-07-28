"""Executable builder script for Ren'Py Asset Extraction Tool.

Invokes PyInstaller programmatically to generate a single-file, windowless executable.
"""

import PyInstaller.__main__


def main() -> None:
    """Executes the PyInstaller build compiler."""
    args = [
        "main.py",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--name=RenPyExtractor",
        "--collect-all=customtkinter",
    ]

    print("Starting PyInstaller compilation for RenPyExtractor.exe...")
    PyInstaller.__main__.run(args)
    print("Executable build complete. Output is in the 'dist' directory.")


if __name__ == "__main__":
    main()
