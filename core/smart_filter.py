"""Smart Search & Filter HUD engine.

Provides dynamic query parsing (dimensions, file sizes, duration, regex, categories)
and manages export preset configurations.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from core.logger import logger


class SmartFilterEngine:
    """Evaluates dynamic search queries against asset metadata dictionaries."""

    @staticmethod
    def parse_size(size_str: str) -> Optional[float]:
        """Converts size strings like '2MB', '500KB', '1.5GB', '1024' into bytes."""
        m = re.match(r"^(\d+(?:\.\d+)?)\s*([a-zA-Z]*)$", size_str.strip())
        if not m:
            return None
        val = float(m.group(1))
        unit = m.group(2).upper()
        if unit in ("K", "KB"):
            return val * 1024
        elif unit in ("M", "MB"):
            return val * 1024 * 1024
        elif unit in ("G", "GB"):
            return val * 1024 * 1024 * 1024
        elif unit in ("B", ""):
            return val
        return None

    @staticmethod
    def filter_assets(assets: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Filters asset metadata dicts based on query expression.

        Supported operators/tokens:
          - width > 1920 / w >= 1080
          - height <= 720 / h < 720
          - duration > 60 / dur < 10
          - size > 2MB / size <= 500KB
          - cat:images / cat:audio / cat:video / cat:scripts
          - ext:png / ext:ogg
          - re:^bg_.* (regex search)
          - text search term (case-insensitive substring match)

        Args:
            assets: List of asset metadata dictionaries.
            query: The filter query string.

        Returns:
            Filtered list of asset metadata dictionaries.
        """
        if not query or not query.strip():
            return assets

        # Normalize spaces around operators (e.g. 'width >= 1080' -> 'width>=1080')
        norm_query = re.sub(r"\b(width|w|height|h|duration|dur|size)\s*([><=]+)\s*", r"\1\2", query.strip(), flags=re.IGNORECASE)
        tokens = norm_query.split()
        filtered = assets

        for token in tokens:
            # Dimension: width / w
            m_w = re.match(r"^(?:width|w)\s*([><=]+)\s*(\d+)$", token, re.IGNORECASE)
            if m_w:
                op, val = m_w.group(1), int(m_w.group(2))
                filtered = [a for a in filtered if SmartFilterEngine._eval_num(a.get("width"), op, val)]
                continue

            # Dimension: height / h
            m_h = re.match(r"^(?:height|h)\s*([><=]+)\s*(\d+)$", token, re.IGNORECASE)
            if m_h:
                op, val = m_h.group(1), int(m_h.group(2))
                filtered = [a for a in filtered if SmartFilterEngine._eval_num(a.get("height"), op, val)]
                continue

            # Duration: duration / dur
            m_d = re.match(r"^(?:duration|dur)\s*([><=]+)\s*(\d+(?:\.\d+)?)$", token, re.IGNORECASE)
            if m_d:
                op, val = m_d.group(1), float(m_d.group(2))
                filtered = [a for a in filtered if SmartFilterEngine._eval_num(a.get("duration"), op, val)]
                continue

            # File Size: size
            m_s = re.match(r"^size\s*([><=]+)\s*([0-9a-zA-Z\.]+)$", token, re.IGNORECASE)
            if m_s:
                op = m_s.group(1)
                bytes_val = SmartFilterEngine.parse_size(m_s.group(2))
                if bytes_val is not None:
                    filtered = [a for a in filtered if SmartFilterEngine._eval_num(a.get("size_bytes"), op, bytes_val)]
                continue

            # Category filter: cat:audio
            if token.lower().startswith("cat:"):
                cat_val = token[4:].strip().lower()
                filtered = [a for a in filtered if a.get("category", "").lower() == cat_val]
                continue

            # Extension filter: ext:png
            if token.lower().startswith("ext:"):
                ext_val = token[4:].strip().lower()
                if not ext_val.startswith("."):
                    ext_val = "." + ext_val
                filtered = [a for a in filtered if a.get("name", "").lower().endswith(ext_val) or a.get("rel_path", "").lower().endswith(ext_val)]
                continue

            # Regex search: re:^bg_.*
            if token.lower().startswith("re:"):
                pattern_str = token[3:]
                try:
                    pat = re.compile(pattern_str, re.IGNORECASE)
                    filtered = [a for a in filtered if pat.search(a.get("name", "")) or pat.search(a.get("rel_path", ""))]
                except re.error:
                    logger.warning(f"Invalid regex pattern: {pattern_str}")
                continue

            # General substring text match
            term = token.lower()
            filtered = [
                a for a in filtered
                if term in a.get("name", "").lower() or term in a.get("rel_path", "").lower()
            ]

        return filtered

    @staticmethod
    def _eval_num(val: Optional[Union[int, float]], op: str, target: Union[int, float]) -> bool:
        if val is None:
            return False
        if op in (">", "gt"):
            return val > target
        elif op in (">=", "gte", "=>"):
            return val >= target
        elif op in ("<", "lt"):
            return val < target
        elif op in ("<=", "lte", "=<"):
            return val <= target
        elif op in ("==", "=", "eq"):
            return val == target
        return False


class PresetManager:
    """Manages saving and loading of asset export presets to JSON storage."""

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path.home() / ".renpy_extractor_presets.json"

        self.presets: Dict[str, str] = self._load_presets()

    def _load_presets(self) -> Dict[str, str]:
        if not self.storage_path.exists():
            default_presets = {
                "Background Music": "cat:audio duration > 30",
                "High-Res Sprites": "cat:images width >= 1080",
                "Large Files": "size > 10MB",
                "Ren'Py Scripts": "ext:rpy ext:rpyc",
            }
            self.save_all(default_presets)
            return default_presets

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load presets: {e}")
            return {}

    def save_all(self, presets: Dict[str, str]) -> None:
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(presets, f, indent=2)
            self.presets = presets
        except Exception as e:
            logger.error(f"Failed to save presets: {e}")

    def add_preset(self, name: str, query: str) -> None:
        self.presets[name] = query
        self.save_all(self.presets)

    def remove_preset(self, name: str) -> None:
        if name in self.presets:
            del self.presets[name]
            self.save_all(self.presets)

    def get_preset(self, name: str) -> Optional[str]:
        return self.presets.get(name)
