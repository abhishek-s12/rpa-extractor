"""RPA Archive Repacker (Compiler) module.

Provides capabilities to package directories or asset dictionaries back into
valid encrypted/obfuscated Ren'Py Archive (.rpa) v3 and v2 files.
"""

import os
import pickle
import zlib
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Tuple, Union
from core.logger import logger


class RpaArchiveWriter:
    """Creates Ren'Py Archive (.rpa) files from a set of target files or directories."""

    def __init__(self, output_path: Union[str, Path], format_version: str = "RPA-3.0", key: Optional[int] = None) -> None:
        """Initializes the RPA Archive Writer.

        Args:
            output_path: Path where the compiled .rpa file will be saved.
            format_version: 'RPA-3.0' or 'RPA-2.0'. Defaults to 'RPA-3.0'.
            key: 32-bit integer XOR key for RPA-3.0. If None, a default key (0x0424b2b4) is generated.
        """
        self.output_path = Path(output_path).resolve()
        self.format_version = format_version.upper()
        if self.format_version not in ("RPA-3.0", "RPA-2.0"):
            raise ValueError(f"Unsupported format version: {format_version}. Use 'RPA-3.0' or 'RPA-2.0'.")

        if self.format_version == "RPA-3.0":
            self.key = key if key is not None else 0x0424b2b4
        else:
            self.key = 0

    def add_directory(self, source_dir: Union[str, Path], base_rel_path: Optional[str] = None) -> Dict[str, Path]:
        """Scans a directory recursively and builds a mapping of relative archive paths to source file paths.

        Args:
            source_dir: Directory containing files to pack.
            base_rel_path: Optional prefix path inside the archive.

        Returns:
            Dictionary mapping relative file paths to absolute source file paths.
        """
        src_path = Path(source_dir).resolve()
        if not src_path.is_dir():
            raise NotADirectoryError(f"Source directory does not exist: {src_path}")

        file_map: Dict[str, Path] = {}
        for root, _, files in os.walk(src_path):
            for fname in files:
                full_path = Path(root) / fname
                rel_path = full_path.relative_to(src_path).as_posix()
                if base_rel_path:
                    rel_path = f"{base_rel_path.strip('/')}/{rel_path}"
                file_map[rel_path] = full_path

        return file_map

    def pack(self, file_map: Mapping[str, Union[str, Path]], progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Path:
        """Packs files specified in file_map into the RPA archive.

        Args:
            file_map: Dictionary mapping archive internal path (e.g. 'images/bg.png')
                      to local file Path or raw bytes.
            progress_callback: Optional callable(current, total, current_file) for progress updates.

        Returns:
            The Path to the created .rpa archive file.
        """
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        raw_index: Dict[str, List[Tuple[int, int, bytes]]] = {}

        temp_archive_path = self.output_path.with_suffix(".tmp")
        total_files = len(file_map)

        logger.info(f"Starting RPA repacking ({self.format_version}) to {self.output_path} with {total_files} files.")

        with open(temp_archive_path, "wb") as f:
            # Write a placeholder header (will overwrite once index offset is known)
            if self.format_version == "RPA-3.0":
                header = f"RPA-3.0 0000000000000000 {self.key:08x}\n".encode("utf-8")
            else:
                header = "RPA-2.0 0000000000000000\n".encode("utf-8")
            f.write(header)

            current_offset = f.tell()
            for idx, (archive_path, src) in enumerate(file_map.items(), 1):
                if isinstance(src, (str, Path)):
                    src_file = Path(src)
                    if not src_file.exists():
                        logger.warning(f"File not found during RPA pack: {src_file}. Skipping.")
                        continue
                    with open(src_file, "rb") as sf:
                        data = sf.read()
                elif isinstance(src, bytes):
                    data = src
                else:
                    raise TypeError(f"Invalid source type for file '{archive_path}': {type(src)}")

                length = len(data)
                offset = current_offset
                f.write(data)
                current_offset += length

                # Obfuscate offset and length if key is non-zero
                obf_offset = offset ^ self.key if self.key else offset
                obf_length = length ^ self.key if self.key else length

                raw_index[archive_path] = [(obf_offset, obf_length, b"")]

                if progress_callback:
                    progress_callback(idx, total_files, archive_path)

            # Record final index offset
            index_offset = f.tell()

            # Pickle and compress index
            pickled_index = pickle.dumps(raw_index, protocol=2)
            compressed_index = zlib.compress(pickled_index)
            f.write(compressed_index)

            # Seek to start and write final header with exact index offset
            f.seek(0)
            if self.format_version == "RPA-3.0":
                final_header = f"RPA-3.0 {index_offset:016x} {self.key:08x}\n".encode("utf-8")
            else:
                final_header = f"RPA-2.0 {index_offset:016x}\n".encode("utf-8")

            f.write(final_header)

        # Replace temp file with final output path
        if temp_archive_path.exists():
            if self.output_path.exists():
                self.output_path.unlink()
            temp_archive_path.rename(self.output_path)

        logger.info(f"RPA archive repacking completed successfully: {self.output_path}")
        return self.output_path
