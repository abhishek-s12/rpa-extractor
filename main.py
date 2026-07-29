"""Main entrypoint for the Ren'Py Asset Extraction Tool.

Provides CLI commands for headless scanning/unpacking and launches the desktop GUI.
"""

import sys
from pathlib import Path
from typing import List, Optional
import typer
from core.archive_reader import RpaArchiveReader
from core.logger import logger, setup_logger
from core.metadata import MetadataManager
from core.scanner import AssetScanner
from core.settings import BaseSettings

# Initialize Typer App
app = typer.Typer(help="Professional-grade Ren'Py Asset Extraction Tool.")


@app.command(name="scan")
def scan_cmd(
    path: Path = typer.Argument(..., help="Path to the game folder or archive to scan."),
) -> None:
    """Scans a game directory or RPA archive and logs contents."""
    setup_logger(debug=False)
    logger.info(f"Starting command-line scan of: {path}")

    if not path.exists():
        logger.error(f"Path does not exist: {path}")
        raise typer.Exit(code=1)

    scanner = AssetScanner(path)
    scanner.scan()

    # Log summary
    logger.info("--- Scan Summary ---")
    logger.info(f"Archives found: {len(scanner.archives)}")
    for arch in scanner.archives:
        logger.info(f"  - {arch.name}")
        try:
            reader = RpaArchiveReader(arch)
            index = reader.read_index()
            logger.info(f"    (Contains {len(index)} packaged files)")
        except Exception as e:
            logger.error(f"    (Failed to read index: {e})")

    logger.info("Loose assets found:")
    for cat, assets in scanner.standalone_assets.items():
        if assets:
            logger.info(f"  - {cat.capitalize()}: {len(assets)} files")


@app.command(name="extract")
def extract_cmd(
    path: Path = typer.Argument(..., help="Path to the game folder or archive to extract."),
    output: Path = typer.Option(..., "--output", "-o", help="Directory where files will be extracted."),
    category: Optional[List[str]] = typer.Option(
        None,
        "--category",
        "-c",
        help="Category to extract (images, audio, video, fonts, scripts, data). Can specify multiple times. If not set, extracts everything.",
    ),
    overwrite: str = typer.Option(
        "skip",
        "--overwrite",
        help="Overwrite behavior for existing files: 'skip', 'overwrite', 'rename'.",
    ),
    fast: bool = typer.Option(
        True,
        "--fast",
        "-f",
        help="Skip hashing and detailed metadata extraction to dramatically speed up unpacking.",
    ),
) -> None:
    """Extracts assets from target game folder or archives, preserving folder structures."""
    setup_logger(debug=False)
    logger.info(f"Starting command-line extraction from {path} to {output} (fast_mode={fast})")

    if not path.exists():
        logger.error(f"Path does not exist: {path}")
        raise typer.Exit(code=1)

    if overwrite not in ("skip", "overwrite", "rename"):
        logger.error(f"Invalid overwrite mode: {overwrite}. Choose from skip, overwrite, rename.")
        raise typer.Exit(code=1)

    try:
        output.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create output folder {output}: {e}")
        raise typer.Exit(code=1)

    # Walk assets
    scanner = AssetScanner(path)
    scanner.scan()

    meta_mgr = MetadataManager(output)
    total_extracted = 0

    # 1. Process Archives
    for rpa in scanner.archives:
        logger.info(f"Extracting archive: {rpa.name}")
        try:
            reader = RpaArchiveReader(rpa)
            index_dict = reader.read_index()
            files = reader.get_filtered_files(category)
            for fname in files:
                extracted_path = reader.extract_file(fname, output, overwrite)
                size_bytes = sum(length for _, length, _ in index_dict[fname])
                meta_mgr.register_file(
                    rel_path=fname,
                    original_source=rpa.name,
                    file_path=extracted_path,
                    fast_mode=fast,
                    size_bytes=size_bytes,
                )
                total_extracted += 1
        except Exception as e:
            logger.error(f"Failed to process archive {rpa.name}: {e}")

    # 2. Process Standalone Files
    import shutil

    active_cats = category if category else list(scanner.standalone_assets.keys())
    for cat, assets in scanner.standalone_assets.items():
        if cat in active_cats:
            for asset_path in assets:
                try:
                    rel_path = str(asset_path.relative_to(scanner.target_path))
                except ValueError:
                    rel_path = asset_path.name

                dest_path = (output / rel_path).resolve()

                if not dest_path.exists() or overwrite == "overwrite":
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(asset_path, dest_path)

                meta_mgr.register_file(
                    rel_path=rel_path,
                    original_source="standalone",
                    file_path=dest_path,
                    fast_mode=fast,
                    size_bytes=asset_path.stat().st_size,
                )
                total_extracted += 1

    # Save manifest
    meta_mgr.save()
    logger.info(f"Extraction complete. Successfully extracted {total_extracted} files.")


@app.command(name="repack")
def repack_cmd(
    source: Path = typer.Argument(..., help="Path to folder containing assets to pack into RPA."),
    output: Path = typer.Option(..., "--output", "-o", help="Target output .rpa file path."),
    version: str = typer.Option("RPA-3.0", "--version", "-v", help="Archive format version: 'RPA-3.0' or 'RPA-2.0'."),
    key: str = typer.Option("0424b2b4", "--key", "-k", help="Hexadecimal XOR encryption key for RPA-3.0."),
) -> None:
    """Packs a directory of customized files into an encrypted Ren'Py Archive (.rpa)."""
    setup_logger(debug=False)
    logger.info(f"Starting CLI repack of {source} -> {output}")
    try:
        from core.rpa_repacker import RpaArchiveWriter

        key_val = int(key, 16) if key else 0x0424b2b4
        writer = RpaArchiveWriter(output, format_version=version, key=key_val)
        file_map = writer.add_directory(source)
        writer.pack(file_map)
        logger.info(f"Successfully packed {len(file_map)} files into {output}")
    except Exception as e:
        logger.error(f"Repack command failed: {e}")
        raise typer.Exit(code=1)


@app.command(name="decompile")
def decompile_cmd(
    path: Path = typer.Argument(..., help="Path to .rpyc file or directory containing .rpyc files."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory or file path for decompiled .rpy script(s)."),
) -> None:
    """Decompiles Ren'Py compiled script files (.rpyc) back into editable .rpy scripts."""
    setup_logger(debug=False)
    logger.info(f"Starting CLI decompile for {path}")
    try:
        from parsers.rpyc_decompiler import RpycDecompiler

        if path.is_file():
            out_file = output if output else path.with_suffix(".rpy")
            text = RpycDecompiler.decompile(path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(text)
            logger.info(f"Decompiled script saved to: {out_file}")
        elif path.is_dir():
            out_dir = output if output else path
            out_dir.mkdir(parents=True, exist_ok=True)
            count = 0
            for rpyc in path.rglob("*.rpyc"):
                dest = out_dir / f"{rpyc.stem}.rpy"
                text = RpycDecompiler.decompile(rpyc)
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(text)
                count += 1
            logger.info(f"Successfully decompiled {count} .rpyc files in {path}")
        else:
            logger.error(f"Invalid path: {path}")
            raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Decompile command failed: {e}")
        raise typer.Exit(code=1)


@app.command(name="gui")
def gui_cmd(debug: bool = typer.Option(False, "--debug", help="Enable debug logs in app log file.")) -> None:
    """Launches the PySide6 desktop GUI application."""
    setup_logger(debug=debug)
    logger.info("Launching PySide6 desktop GUI...")
    try:
        from ui.app_qt import main_qt

        main_qt()
    except Exception as e:
        logger.critical(f"Failed to start GUI application: {e}")
        sys.exit(1)


def main() -> None:
    """Entrypoint redirection."""
    # If launched with no arguments, default to launching the GUI
    if len(sys.argv) == 1:
        sys.argv.append("gui")
    app()


if __name__ == "__main__":
    main()

