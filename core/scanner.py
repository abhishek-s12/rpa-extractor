"""Directory scanner and game detection engine.

Scans paths to identify Ren'Py game subdirectories, RPA archives, and standalone assets.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set
from core.config import SUPPORTED_EXTENSIONS
from core.logger import logger


class AssetScanner:
    """Recursively crawls directories and categorizes files based on configurations."""

    def __init__(self, target_path: Path) -> None:
        """Initializes the scanner with a target path.

        Args:
            target_path: Path to the directory or file to scan.
        """
        self.target_path = target_path.resolve()
        self.game_dir: Optional[Path] = None
        self.is_game_folder: bool = False
        self.archives: List[Path] = []
        self.standalone_assets: Dict[str, List[Path]] = {
            cat: [] for cat in SUPPORTED_EXTENSIONS.keys()
        }
        self.standalone_assets["other"] = []

        self.detect_game_structure()

    def detect_game_structure(self) -> None:
        """Inspects target path to see if it represents a Ren'Py game folder structure.

        Checks for the standard 'game' subdirectory and compiles list of .rpa archives.
        """
        if not self.target_path.exists():
            logger.warning(f"Target path {self.target_path} does not exist.")
            return

        if self.target_path.is_file():
            # If target is a file, check if it's an archive
            if self.target_path.suffix.lower() == ".rpa":
                self.archives.append(self.target_path)
            return

        # Check if the folder itself contains 'game/' directory or acts as the game directory
        game_sub = self.target_path / "game"
        if game_sub.exists() and game_sub.is_dir():
            self.game_dir = game_sub
            self.is_game_folder = True
            logger.info(f"Detected Ren'Py game directory structure: {game_sub}")
        elif self.target_path.name == "game" or (self.target_path / "renpy").exists():
            self.game_dir = self.target_path
            self.is_game_folder = True
            logger.info(f"Target path matches a Ren'Py game/renpy directory: {self.target_path}")
        else:
            self.game_dir = self.target_path
            logger.info(f"Target path treated as a general directory: {self.target_path}")

    def scan(self, categories: Optional[List[str]] = None) -> Dict[str, List[Path]]:
        """Scans the target path and classifies files into matching categories.

        Args:
            categories: Optional list of categories to scan. If None, scans all categories.

        Returns:
            A dictionary containing lists of categorized file Paths.
        """
        # Clear previous scans
        self.archives.clear()
        for cat in self.standalone_assets:
            self.standalone_assets[cat].clear()

        if not self.target_path.exists():
            return self.standalone_assets

        # Compile set of allowed extensions based on filters
        allowed_extensions: Set[str] = set()
        active_cats = categories if categories is not None else list(SUPPORTED_EXTENSIONS.keys())

        for cat in active_cats:
            if cat in SUPPORTED_EXTENSIONS:
                allowed_extensions.update(SUPPORTED_EXTENSIONS[cat])

        # Walk directory tree
        if self.target_path.is_file():
            self._classify_file(self.target_path, active_cats, allowed_extensions)
        else:
            self._scan_directory(self.target_path, active_cats, allowed_extensions)

        logger.info(
            f"Scan completed. Found {len(self.archives)} archives and "
            f"{sum(len(v) for v in self.standalone_assets.values())} standalone assets."
        )
        return self.standalone_assets

    def _scan_directory(self, folder: Path, active_cats: List[str], allowed_extensions: Set[str]) -> None:
        """Helper to walk the filesystem recursively."""
        try:
            for item in folder.rglob("*"):
                if item.is_file():
                    self._classify_file(item, active_cats, allowed_extensions)
        except Exception as e:
            logger.error(f"Error scanning directory {folder}: {e}")

    def _classify_file(self, file_path: Path, active_cats: List[str], allowed_extensions: Set[str]) -> None:
        """Checks file extension and adds path to correct catalog."""
        suffix = file_path.suffix.lower()

        # Archive detection (always scan archives)
        if suffix == ".rpa":
            self.archives.append(file_path)
            return

        # Classification into filtered categories
        classified = False
        for cat, exts in SUPPORTED_EXTENSIONS.items():
            if cat in active_cats and suffix in exts:
                self.standalone_assets[cat].append(file_path)
                classified = True
                break

        # If not classified but we are scanning everything, put into 'other'
        if not classified and categories_include_all(active_cats):
            self.standalone_assets["other"].append(file_path)


def categories_include_all(active_cats: List[str]) -> bool:
    """Helper to check if all supported categories are active."""
    return len(active_cats) >= len(SUPPORTED_EXTENSIONS)
