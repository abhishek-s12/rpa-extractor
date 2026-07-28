"""Unit tests for the Ren'Py archive reader and extraction logic.

Programmatically generates mock RPA archives and runs parsing tests on them.
"""

import pickle
import tempfile
import zlib
from pathlib import Path
from typing import Generator
import pytest
from core.archive_reader import RpaArchiveReader


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Temporary directory fixture for building mock archives."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_rpa_2_0_parsing(temp_dir: Path) -> None:
    """Verifies parsing and extraction of RPAv2 archives."""
    archive_path = temp_dir / "test_v2.rpa"
    output_dir = temp_dir / "output"

    # Dummy file contents
    file1_data = b"Hello from image 1"
    file2_data = b"Hello from audio 2"
    prefix = b"Made with Ren'Py."

    # Build file index mapping
    # RPAv2 index: {filename: [(offset, length, prefix)]}
    # File 1 starts at offset 100
    # File 2 starts at offset 200
    index_dict = {
        "images/bg.png": [(100, len(file1_data), prefix)],
        "audio/bgm.ogg": [(200, len(file2_data), b"")],
    }

    # Compress and pickle index
    pickled = pickle.dumps(index_dict)
    compressed = zlib.compress(pickled)

    # Write archive
    # RPA-2.0 [index_offset]
    index_offset = 300
    header = f"RPA-2.0 {index_offset:016x}\n".encode("utf-8")

    with open(archive_path, "wb") as f:
        f.write(header)
        # Write dummy data at file offsets
        f.seek(100)
        f.write(file1_data)
        f.seek(200)
        f.write(file2_data)
        # Write index at offset
        f.seek(index_offset)
        f.write(compressed)

    # Instantiate Reader and test
    reader = RpaArchiveReader(archive_path)
    assert reader.format_version == "RPA-2.0"
    assert reader.index_offset == index_offset

    index = reader.read_index()
    assert "images/bg.png" in index
    assert "audio/bgm.ogg" in index

    # Verify offset/length/prefix contents
    assert index["images/bg.png"][0][0] == 100
    assert index["images/bg.png"][0][1] == len(file1_data)
    assert index["images/bg.png"][0][2] == prefix

    # Test extraction
    out_file1 = reader.extract_file("images/bg.png", output_dir)
    assert out_file1.exists()
    with open(out_file1, "rb") as out_f:
        # Extracted content should combine prefix + data
        assert out_f.read() == prefix + file1_data


def test_rpa_3_0_parsing(temp_dir: Path) -> None:
    """Verifies decryption, index unpickling, and extraction of RPAv3 archives."""
    archive_path = temp_dir / "test_v3.rpa"
    output_dir = temp_dir / "output"

    key = 0xDEADC0DE
    file_data = b"Encrypted data block"
    prefix = b"Made with Ren'Py."
    file_offset = 150
    file_len = len(file_data)

    # RPAv3 index dictionary contains XORed offsets and lengths:
    # offset ^ key, length ^ key
    index_dict = {
        "images/char.png": [(file_offset ^ key, file_len ^ key, prefix)],
    }

    pickled = pickle.dumps(index_dict)
    compressed = zlib.compress(pickled)

    # Header: RPA-3.0 [index_offset] [key]
    index_offset = 400
    header = f"RPA-3.0 {index_offset:016x} {key:08x}\n".encode("utf-8")

    with open(archive_path, "wb") as f:
        f.write(header)
        f.seek(file_offset)
        f.write(file_data)
        f.seek(index_offset)
        f.write(compressed)

    # Instantiate Reader and test
    reader = RpaArchiveReader(archive_path)
    assert reader.format_version == "RPA-3.0"
    assert reader.index_offset == index_offset
    assert reader.key == key

    index = reader.read_index()
    assert "images/char.png" in index
    
    # Assert deobfuscation was successful
    assert index["images/char.png"][0][0] == file_offset
    assert index["images/char.png"][0][1] == file_len

    # Test extraction
    out_file = reader.extract_file("images/char.png", output_dir)
    assert out_file.exists()
    with open(out_file, "rb") as out_f:
        assert out_f.read() == prefix + file_data
