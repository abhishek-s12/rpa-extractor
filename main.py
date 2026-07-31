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


@app.command(name="translate")
def translate_cmd(
    path: Path = typer.Argument(..., help="Path to .rpy file or directory containing .rpy scripts."),
    target_lang: str = typer.Option("Spanish", "--target-lang", "-l", help="Target language for translation."),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="Gemini API Key (uses offline mode if not set)."),
) -> None:
    """Translates Ren'Py .rpy scripts using AI translation pipeline preserving text formatting tags."""
    setup_logger(debug=False)
    logger.info(f"Starting CLI script translation for {path} into {target_lang}")
    try:
        from parsers.translation_engine import RenpyScriptTranslator
        translator = RenpyScriptTranslator(api_key=api_key, target_lang=target_lang)
        if path.is_file():
            out = translator.translate_script_file(path)
            logger.info(f"Translated script saved: {out}")
        elif path.is_dir():
            out_dir = path.parent / f"{path.name}_{target_lang.lower()}"
            res = translator.translate_directory(path, out_dir)
            logger.info(f"Translated {len(res)} scripts into {out_dir}")
    except Exception as e:
        logger.error(f"Translation command failed: {e}")
        raise typer.Exit(code=1)


@app.command(name="tag")
def tag_cmd(
    path: Path = typer.Argument(..., help="Extracted assets directory path to tag and index."),
) -> None:
    """Indexes asset metadata with AI emotion, character sprite, and background scene tags."""
    setup_logger(debug=False)
    logger.info(f"Starting AI asset tagging for {path}")
    try:
        from extractors.image_tagger import SmartMetadataIndexer
        catalog = SmartMetadataIndexer.index_directory(path)
        logger.info(f"Successfully tagged {len(catalog)} assets in metadata.json")
    except Exception as e:
        logger.error(f"Tag command failed: {e}")
        raise typer.Exit(code=1)


@app.command(name="watch")
def watch_cmd(
    watch_dir: Path = typer.Argument(..., help="Modded asset directory to watch for live hot-reloading."),
    game_dir: Optional[Path] = typer.Option(None, "--game-dir", "-g", help="Target Ren'Py game directory for RPA override injection."),
) -> None:
    """Watches asset folder for changes and live-reloads modified sprites and audio in-game."""
    setup_logger(debug=False)
    logger.info(f"Starting Hot-Reloading Studio watcher on {watch_dir}")
    try:
        from core.live_interceptor import HotReloadStudio, RenPyProcessHooker
        if game_dir:
            RenPyProcessHooker.inject_rpa_override_hook(game_dir, watch_dir)

        studio = HotReloadStudio(watch_dir)
        studio.start()
        logger.info("Watcher running. Press Ctrl+C to exit.")
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            studio.stop()
    except Exception as e:
        logger.error(f"Watch command failed: {e}")
        raise typer.Exit(code=1)


@app.command(name="diff")
def diff_cmd(
    v1: Path = typer.Argument(..., help="Path to Version 1 asset directory."),
    v2: Path = typer.Argument(..., help="Path to Version 2 asset directory."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output folder for diff report and pixel heatmaps."),
) -> None:
    """Compares two asset version releases and generates visual/audio difference reports."""
    setup_logger(debug=False)
    logger.info(f"Starting version diff: {v1} vs {v2}")
    try:
        from core.version_diff import AssetVersionComparator
        report = AssetVersionComparator.compare_directories(v1, v2, output)
        logger.info(f"Diff Summary: {report['summary']}")
    except Exception as e:
        logger.error(f"Diff command failed: {e}")
        raise typer.Exit(code=1)


@app.command(name="upscale")
def upscale_cmd(
    path: Path = typer.Argument(..., help="Path to image file or directory of images."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Target output file or folder."),
    scale: int = typer.Option(2, "--scale", "-s", help="Scale factor: 2 or 4."),
    clean_alpha: bool = typer.Option(False, "--clean-alpha", help="Apply alpha-channel edge de-fringing."),
) -> None:
    """Upscales visual novel sprites and CG backgrounds with AI 4K texture upscaler."""
    setup_logger(debug=False)
    logger.info(f"Starting texture upscaler for {path} (scale={scale}x, clean_alpha={clean_alpha})")
    try:
        from extractors.media_pipeline import SpriteCleaner, TextureUpscaler
        if path.is_file():
            out_p = output if output else path.parent / f"{path.stem}_{scale}x{path.suffix}"
            TextureUpscaler.upscale_image(path, out_p, scale=scale)
            if clean_alpha:
                SpriteCleaner.clean_transparency(out_p, out_p)
            logger.info(f"Processed image saved to: {out_p}")
        elif path.is_dir():
            out_dir = output if output else path.parent / f"{path.name}_{scale}x"
            out_dir.mkdir(parents=True, exist_ok=True)
            for img in path.rglob("*.*"):
                if img.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                    rel = img.relative_to(path)
                    dest = out_dir / rel
                    TextureUpscaler.upscale_image(img, dest, scale=scale)
                    if clean_alpha:
                        SpriteCleaner.clean_transparency(dest, dest)
            logger.info(f"Successfully processed directory: {out_dir}")
    except Exception as e:
        logger.error(f"Upscale command failed: {e}")
        raise typer.Exit(code=1)


@app.command(name="transcode")
def transcode_cmd(
    input_dir: Path = typer.Argument(..., help="Input directory containing media assets."),
    output_dir: Path = typer.Argument(..., help="Output directory for transcoded assets."),
    audio_format: str = typer.Option("ogg", "--audio-format", "-a", help="Audio target format: 'ogg' or 'opus'."),
    image_format: str = typer.Option("webp", "--image-format", "-i", help="Image target format: 'webp' or 'avif'."),
) -> None:
    """Batch transcodes audio assets to OGG/Opus and images to WebP/AVIF."""
    setup_logger(debug=False)
    logger.info(f"Starting batch transcoding from {input_dir} to {output_dir}")
    try:
        from extractors.media_pipeline import BatchTranscoder
        stats = BatchTranscoder.transcode_directory(input_dir, output_dir, audio_format=audio_format, image_format=image_format)
        logger.info(f"Batch transcoding complete: {stats}")
    except Exception as e:
        logger.error(f"Transcode command failed: {e}")
        raise typer.Exit(code=1)


@app.command(name="plugin")
def plugin_cmd(
    action: str = typer.Argument("list", help="Action: 'list' or 'discover'"),
    plugin_dir: Optional[Path] = typer.Option(None, "--dir", "-d", help="Directory containing python plugins to discover."),
) -> None:
    """Manages community extractor plugins and decryptor extensions."""
    setup_logger(debug=False)
    try:
        from core.plugin_sdk import PluginRegistry
        if action == "discover" and plugin_dir:
            count = PluginRegistry.discover_plugins(plugin_dir)
            logger.info(f"Discovered and loaded {count} new plugins from {plugin_dir}")

        plugins = PluginRegistry.list_plugins()
        logger.info("--- Registered Plugins ---")
        for p in plugins:
            logger.info(f"  - {p['name']} v{p['version']} by {p['author']}: {p['description']}")
    except Exception as e:
        logger.error(f"Plugin command failed: {e}")
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

