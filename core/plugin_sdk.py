"""Plugin SDK and Registry for Ren'Py Asset Extractor.

Enables community developers to register custom XOR decryption schemes, encrypted
pickle formats, and custom RPA/archive headers.
"""

from abc import ABC, abstractmethod
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from core.logger import logger


class BaseExtractorPlugin(ABC):
    """Abstract base class for community extractor plugins."""

    plugin_name: str = "BasePlugin"
    plugin_version: str = "1.0.0"
    author: str = "Community"
    description: str = "Base plugin interface"

    @abstractmethod
    def can_handle(self, file_path: Path, header_bytes: bytes) -> bool:
        """Determines whether this plugin can handle the given file or archive header."""
        pass

    @abstractmethod
    def read_index(self, file_path: Path) -> Dict[str, Any]:
        """Reads archive index/table of contents for custom archive formats.

        Returns:
            Dictionary mapping relative file paths to list of (offset, length, key) tuples.
        """
        pass

    def decrypt_data(self, data: bytes, key: Optional[int] = None) -> bytes:
        """Applies custom XOR key or decryption algorithm to raw file bytes."""
        if key is None or key == 0:
            return data
        return bytes([b ^ (key & 0xFF) for b in data])

    def extract_file(
        self,
        file_path: Path,
        rel_path: str,
        output_dir: Path,
        offset: int = 0,
        length: int = 0,
        key: Optional[int] = None,
    ) -> Path:
        """Extracts a single file using custom decryption logic."""
        dest_path = output_dir / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "rb") as f:
            f.seek(offset)
            raw = f.read(length) if length > 0 else f.read()

        decrypted = self.decrypt_data(raw, key=key)
        with open(dest_path, "wb") as f_out:
            f_out.write(decrypted)

        return dest_path


class PluginRegistry:
    """Central registry managing loaded community extractor plugins."""

    _plugins: List[BaseExtractorPlugin] = []

    @classmethod
    def register(cls, plugin: BaseExtractorPlugin) -> None:
        """Registers a new plugin instance."""
        for p in cls._plugins:
            if p.plugin_name == plugin.plugin_name:
                logger.info(f"Plugin {plugin.plugin_name} is already registered. Updating...")
                cls._plugins.remove(p)
                break
        cls._plugins.append(plugin)
        logger.info(f"Registered plugin: {plugin.plugin_name} v{plugin.plugin_version}")

    @classmethod
    def list_plugins(cls) -> List[Dict[str, str]]:
        """Returns metadata for all registered plugins."""
        return [
            {
                "name": p.plugin_name,
                "version": p.plugin_version,
                "author": p.author,
                "description": p.description,
            }
            for p in cls._plugins
        ]

    @classmethod
    def get_plugin_for_file(cls, file_path: Path, header_bytes: bytes) -> Optional[BaseExtractorPlugin]:
        """Finds a registered plugin capable of handling the specified file header."""
        for plugin in cls._plugins:
            try:
                if plugin.can_handle(file_path, header_bytes):
                    return plugin
            except Exception as e:
                logger.warning(f"Error checking plugin {plugin.plugin_name}: {e}")
        return None

    @classmethod
    def discover_plugins(cls, plugin_dir: Path) -> int:
        """Scans a directory for Python plugin files and loads them dynamically."""
        if not plugin_dir.exists() or not plugin_dir.is_dir():
            return 0

        count = 0
        for py_file in plugin_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    for attr_name in dir(mod):
                        attr = getattr(mod, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BaseExtractorPlugin)
                            and attr is not BaseExtractorPlugin
                        ):
                            cls.register(attr())
                            count += 1
            except Exception as e:
                logger.error(f"Failed to load plugin from {py_file}: {e}")

        return count


class StandardXORPlugin(BaseExtractorPlugin):
    """Built-in reference plugin for standard XOR obfuscated Ren'Py archives."""

    plugin_name = "StandardXORDecryptor"
    plugin_version = "1.0.0"
    author = "RenPyExtractor Core"
    description = "Handles standard 4-byte key XOR obfuscated archive files"

    def can_handle(self, file_path: Path, header_bytes: bytes) -> bool:
        return header_bytes.startswith(b"RPA-3.0") or header_bytes.startswith(b"XOR")

    def read_index(self, file_path: Path) -> Dict[str, Any]:
        return {}


# Auto-register default reference plugin
PluginRegistry.register(StandardXORPlugin())
