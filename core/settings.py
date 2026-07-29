"""Settings manager for the Ren'Py Asset Extraction Tool.

Handles saving and loading of application preferences to a local JSON file.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.logger import logger


class AppSettings:
    """Manages application settings and local storage."""

    def __init__(self, settings_path: Optional[Path] = None) -> None:
        """Initializes settings and sets default values.

        Args:
            settings_path: Custom path to save/load settings, defaults to settings.json in app root.
        """
        if settings_path is None:
            import sys
            if getattr(sys, "frozen", False):
                self.settings_path = Path(sys.executable).resolve().parent / "settings.json"
            else:
                self.settings_path = Path(__file__).resolve().parent.parent / "settings.json"
        else:
            self.settings_path = settings_path

        # Default settings configurations
        self.output_dir: str = ""
        self.overwrite_mode: str = "skip"  # Options: overwrite, skip, rename
        self.thread_count: int = min(32, (os.cpu_count() or 4) + 4)
        self.thumbnail_size_w: int = 150
        self.thumbnail_size_h: int = 150
        self.theme: str = "dark"  # Options: dark, light, system
        self.selected_categories: List[str] = [
            "images",
            "audio",
            "video",
            "fonts",
            "scripts",
            "data",
        ]
        self.fast_mode: bool = True

        self.load()

    def to_dict(self) -> Dict[str, Any]:
        """Converts settings fields into a dictionary."""
        return {
            "output_dir": self.output_dir,
            "overwrite_mode": self.overwrite_mode,
            "thread_count": self.thread_count,
            "thumbnail_size_w": self.thumbnail_size_w,
            "thumbnail_size_h": self.thumbnail_size_h,
            "theme": self.theme,
            "selected_categories": self.selected_categories,
            "fast_mode": self.fast_mode,
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Populates settings fields from a dictionary."""
        self.output_dir = data.get("output_dir", self.output_dir)
        self.overwrite_mode = data.get("overwrite_mode", self.overwrite_mode)
        self.thread_count = data.get("thread_count", self.thread_count)
        self.thumbnail_size_w = data.get("thumbnail_size_w", self.thumbnail_size_w)
        self.thumbnail_size_h = data.get("thumbnail_size_h", self.thumbnail_size_h)
        self.theme = data.get("theme", self.theme)
        self.selected_categories = data.get("selected_categories", self.selected_categories)
        self.fast_mode = data.get("fast_mode", self.fast_mode)

    def load(self) -> None:
        """Loads settings from the JSON file if it exists."""
        if not self.settings_path.exists():
            logger.info("Settings file not found. Using default settings.")
            return

        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.from_dict(data)
            logger.debug(f"Loaded settings from {self.settings_path}")
        except Exception as e:
            logger.error(f"Error loading settings from {self.settings_path}: {e}")

    def save(self) -> None:
        """Saves current settings configuration to the JSON file."""
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=4)
            logger.debug(f"Saved settings to {self.settings_path}")
        except Exception as e:
            logger.error(f"Error saving settings to {self.settings_path}: {e}")
            raise
BaseSettings = AppSettings()
