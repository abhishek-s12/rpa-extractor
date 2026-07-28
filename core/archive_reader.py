"""Archive reader and extraction module.

Parses Ren'Py Archive (RPA) indexes, decrypts entries using XOR keys,
and extracts target files by reading chunked data.
"""

import pickle
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from core.archive_detector import ArchiveDetector
from core.config import SUPPORTED_EXTENSIONS
from core.logger import logger


class RpaArchiveReader:
    """Reads and extracts assets from a Ren'Py Archive (.rpa) file."""

    def __init__(self, archive_path: Union[str, Path]) -> None:
        """Initializes the archive reader.

        Args:
            archive_path: Path to the target RPA archive file.
        """
        self.archive_path = Path(archive_path).resolve()
        self.format_version: Optional[str] = None
        self.index_offset: int = 0
        self.key: int = 0
        self.file_index: Dict[str, List[Tuple[int, int, bytes]]] = {}

        self._read_header()

    def _read_header(self) -> None:
        """Reads the RPA file header to extract index offset and XOR key."""
        self.format_version = ArchiveDetector.detect_format(self.archive_path)
        if not self.format_version:
            raise ValueError(f"File is not a valid Ren'Py Archive: {self.archive_path}")

        try:
            with open(self.archive_path, "rb") as f:
                header_line = f.readline().decode("utf-8", errors="ignore").strip()

            parts = header_line.split()
            if self.format_version in ("RPA-3.0", "RPA-3.2"):
                if len(parts) < 3:
                    raise ValueError(f"Malformed RPAv3 header: {header_line}")
                self.index_offset = int(parts[1], 16)
                self.key = int(parts[2], 16)
            elif self.format_version == "RPA-2.0":
                if len(parts) < 2:
                    raise ValueError(f"Malformed RPAv2 header: {header_line}")
                self.index_offset = int(parts[1], 16)
                self.key = 0  # No key/obfuscation for RPAv2
            elif self.format_version == "RPA-1.0":
                # RPAv1 starts directly with the pickled index at the offset
                # For RPAv1, offset is typically at the end or specified.
                # However, RPAv1 is extremely rare. We will default index_offset to 0 or check parts.
                self.index_offset = 0
                self.key = 0
                logger.warning("RPA-1.0 format detected. Support is experimental.")

            logger.debug(
                f"Parsed {self.format_version} header: Offset={self.index_offset}, Key=0x{self.key:08x}"
            )
        except Exception as e:
            logger.error(f"Failed to read archive header for {self.archive_path}: {e}")
            raise

    def read_index(self) -> Dict[str, List[Tuple[int, int, bytes]]]:
        """Loads and deobfuscates the archive file index.

        Returns:
            A dictionary mapping filenames to lists of (offset, length, prefix) tuples.
        """
        if self.file_index:
            return self.file_index

        try:
            with open(self.archive_path, "rb") as f:
                f.seek(self.index_offset)
                compressed_index = f.read()

            # Decompress index
            decompressed_data = zlib.decompress(compressed_index)

            # Unpickle index dict
            # NOTE: pickle.loads is insecure for untrusted files. We use it here to read Ren'Py archives.
            raw_index = pickle.loads(decompressed_data)

            # Deobfuscate file index using the XOR key
            deobfuscated: Dict[str, List[Tuple[int, int, bytes]]] = {}

            for filename, entries in raw_index.items():
                clean_entries: List[Tuple[int, int, bytes]] = []
                for entry in entries:
                    # Entries can be (offset, length, prefix) or (offset, length)
                    if len(entry) >= 2:
                        offset = entry[0]
                        length = entry[1]
                        prefix = entry[2] if len(entry) >= 3 else b""

                        if self.key != 0:
                            # Apply XOR decryption
                            offset = offset ^ self.key
                            length = length ^ self.key

                        # Ensure prefix is bytes
                        if isinstance(prefix, str):
                            prefix = prefix.encode("latin1")

                        clean_entries.append((offset, length, prefix))

                # Some games use backslashes or forward slashes, let's normalize to forward slashes
                normalized_name = filename.replace("\\", "/")
                deobfuscated[normalized_name] = clean_entries

            self.file_index = deobfuscated
            logger.info(f"Loaded index of {self.archive_path} containing {len(deobfuscated)} files.")
            return self.file_index

        except Exception as e:
            logger.error(f"Failed to parse index of archive {self.archive_path}: {e}")
            raise

    def get_filtered_files(self, categories: Optional[List[str]] = None) -> List[str]:
        """Returns list of archive files filtered by categories.

        Args:
            categories: List of categories to keep (e.g. ['audio', 'images']).
                       If None or empty, returns all files.

        Returns:
            A list of matching file paths inside the archive.
        """
        all_files = list(self.read_index().keys())
        if not categories:
            return all_files

        # Build allowed extensions set
        allowed_exts = set()
        for cat in categories:
            if cat in SUPPORTED_EXTENSIONS:
                allowed_exts.update(SUPPORTED_EXTENSIONS[cat])

        filtered = []
        for f in all_files:
            suffix = Path(f).suffix.lower()
            if suffix in allowed_exts:
                filtered.append(f)

        return filtered

    def read_file_bytes(self, filename: str) -> bytes:
        """Reads raw file contents of a specific file inside the archive.

        Args:
            filename: Name of the file to extract (relative path in index).

        Returns:
            The raw bytes of the file.
        """
        index = self.read_index()
        if filename not in index:
            raise KeyError(f"File '{filename}' not found in archive index.")

        entries = index[filename]
        file_bytes = b""

        try:
            with open(self.archive_path, "rb") as f:
                for offset, length, prefix in entries:
                    f.seek(offset)
                    data = f.read(length)
                    file_bytes += prefix + data
            return file_bytes
        except Exception as e:
            logger.error(f"Error reading file bytes for '{filename}' in '{self.archive_path}': {e}")
            raise

    def extract_file(self, filename: str, output_dir: Path, overwrite_mode: str = "skip") -> Path:
        """Extracts a single file from the archive to the specified output directory.

        Args:
            filename: Relative path of the file in the archive.
            output_dir: Destination folder where directory structure is preserved.
            overwrite_mode: Overwrite behavior: 'overwrite', 'skip', or 'rename'.

        Returns:
            The Path of the extracted file.
        """
        out_path = (output_dir / filename).resolve()

        # Handle overwrite behavior
        if out_path.exists():
            if overwrite_mode == "skip":
                logger.debug(f"Skipping existing file: {out_path}")
                return out_path
            elif overwrite_mode == "rename":
                # Add index suffix to filename e.g. path_1.png
                stem = out_path.stem
                suffix = out_path.suffix
                parent = out_path.parent
                counter = 1
                while True:
                    candidate = parent / f"{stem}_{counter}{suffix}"
                    if not candidate.exists():
                        out_path = candidate
                        break
                    counter += 1

        # Read bytes and write to disk
        try:
            data = self.read_file_bytes(filename)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(data)
            logger.debug(f"Successfully extracted: {filename} -> {out_path}")
            return out_path
        except Exception as e:
            logger.error(f"Failed to extract '{filename}' from '{self.archive_path}': {e}")
            raise
