"""Metadata management module.

Gathers extracted file hashes and format details to generate metadata.json manifests.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union
from core.hashing import calculate_hashes, calculate_perceptual_hash
from core.logger import logger
from extractors.audio_extractor import AudioExtractor
from extractors.image_extractor import ImageExtractor
from extractors.video_extractor import VideoExtractor
from parsers.script_parser import ScriptParser


class MetadataManager:
    """Aggregates specifications of extracted files and creates a catalog report."""

    def __init__(self, output_dir: Path) -> None:
        """Initializes the manager with a destination folder.

        Args:
            output_dir: Folder path where metadata.json will be saved.
        """
        self.output_dir = output_dir.resolve()
        self.catalog: Dict[str, Dict[str, Any]] = {}

    def register_file(
        self,
        rel_path: str,
        original_source: str,
        file_bytes: Optional[bytes] = None,
        file_path: Optional[Path] = None,
        fast_mode: bool = False,
        size_bytes: Optional[int] = None,
    ) -> None:
        """Calculates specs and hashes for a file and registers it in the catalog.

        Args:
            rel_path: The relative path inside the output directory.
            original_source: The source RPA archive name or path.
            file_bytes: Raw bytes if processing in-memory.
            file_path: File path on disk if already written.
            fast_mode: If True, bypasses hash calculations and media specs checks.
            size_bytes: Optional pre-calculated file size.
        """
        size = 0
        if size_bytes is not None:
            size = size_bytes
        elif file_bytes is not None:
            size = len(file_bytes)
        elif file_path is not None and file_path.exists():
            size = file_path.stat().st_size

        if fast_mode:
            self.catalog[rel_path] = {
                "original_source": original_source,
                "size_bytes": size,
                "md5": "",
                "sha256": "",
                "perceptual_hash": "",
                "category": "other",
                "details": {},
            }
            return

        target: Union[bytes, Path]
        if file_bytes is not None:
            target = file_bytes
        elif file_path is not None and file_path.exists():
            target = file_path
        else:
            logger.warning(f"Metadata registration failed: no source data for {rel_path}")
            return

        # Calculate hashes
        hashes = calculate_hashes(target)
        suffix = Path(rel_path).suffix.lower()

        # Classify and extract detailed specifications
        category = "other"
        details: Dict[str, Any] = {}
        perceptual_hash = ""

        # Check Category & parse details
        from core.config import SUPPORTED_EXTENSIONS
        for cat, exts in SUPPORTED_EXTENSIONS.items():
            if suffix in exts:
                category = cat
                break

        if category == "images":
            details = ImageExtractor.get_metadata(target)
            perceptual_hash = calculate_perceptual_hash(target)
        elif category == "audio":
            details = AudioExtractor.get_metadata(target)
        elif category == "video":
            details = VideoExtractor.get_metadata(target)
        elif category == "scripts":
            details = ScriptParser.parse_script(target)

        # Store in catalog
        self.catalog[rel_path] = {
            "original_source": original_source,
            "size_bytes": size,
            "md5": hashes.get("md5", ""),
            "sha256": hashes.get("sha256", ""),
            "perceptual_hash": perceptual_hash,
            "category": category,
            "details": details,
        }

    def save(self, filepath: Optional[Path] = None) -> Path:
        """Dumps the registered catalog to a metadata.json file.

        Args:
            filepath: Optional custom file path to write to.

        Returns:
            The Path of the saved metadata file.
        """
        save_path = filepath if filepath is not None else self.output_dir / "metadata.json"
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self.catalog, f, indent=4)
            logger.info(f"Metadata manifest successfully saved to: {save_path}")
            return save_path
        except Exception as e:
            logger.error(f"Failed to save metadata manifest to {save_path}: {e}")
            raise
