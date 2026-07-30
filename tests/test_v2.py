"""Unit tests for Ren'Py Asset Extraction Tool v2.0 features.

Tests RPA archive repacker roundtrips, .rpyc decompiler logic, smart filter engine,
and export preset management.
"""

import os
import tempfile
from pathlib import Path
import pytest
from core.archive_reader import RpaArchiveReader
from core.rpa_repacker import RpaArchiveWriter
from core.smart_filter import PresetManager, SmartFilterEngine
from parsers.rpyc_decompiler import RpycDecompiler


def test_rpa_repacker_roundtrip() -> None:
    """Tests packing files into an RPAv3 archive and reading them back."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create dummy source files
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        (src_dir / "script.rpy").write_text("label start:\n    'Hello World'\n", encoding="utf-8")
        (src_dir / "test.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01")

        rpa_out = tmp_path / "output.rpa"
        writer = RpaArchiveWriter(rpa_out, format_version="RPA-3.0", key=0x12345678)
        file_map = writer.add_directory(src_dir)
        writer.pack(file_map)

        assert rpa_out.exists()

        # Read back using RpaArchiveReader
        reader = RpaArchiveReader(rpa_out)
        index = reader.read_index()

        assert "script.rpy" in index
        assert "test.png" in index

        script_bytes = reader.read_file_bytes("script.rpy")
        assert b"Hello World" in script_bytes


def test_smart_filter_engine() -> None:
    """Tests dynamic query parsing in SmartFilterEngine."""
    assets = [
        {"name": "bg_beach.png", "rel_path": "images/bg_beach.png", "category": "images", "width": 1920, "height": 1080, "size_bytes": 2 * 1024 * 1024},
        {"name": "icon.png", "rel_path": "images/icon.png", "category": "images", "width": 64, "height": 64, "size_bytes": 5 * 1024},
        {"name": "theme.ogg", "rel_path": "audio/theme.ogg", "category": "audio", "duration": 120.5, "size_bytes": 4 * 1024 * 1024},
    ]

    # Test dimension filter
    res_dim = SmartFilterEngine.filter_assets(assets, "width >= 1080")
    assert len(res_dim) == 1
    assert res_dim[0]["name"] == "bg_beach.png"

    # Test category filter
    res_cat = SmartFilterEngine.filter_assets(assets, "cat:audio")
    assert len(res_cat) == 1
    assert res_cat[0]["name"] == "theme.ogg"

    # Test size filter
    res_size = SmartFilterEngine.filter_assets(assets, "size > 1MB")
    assert len(res_size) == 2

    # Test regex search
    res_re = SmartFilterEngine.filter_assets(assets, "re:^bg_.*")
    assert len(res_re) == 1
    assert res_re[0]["name"] == "bg_beach.png"


def test_preset_manager() -> None:
    """Tests saving and retrieving export filter presets."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        json_path = Path(tmp_dir) / "presets.json"
        pm = PresetManager(storage_path=json_path)

        pm.add_preset("Music Only", "cat:audio duration > 30")
        assert pm.get_preset("Music Only") == "cat:audio duration > 30"

        pm.remove_preset("Music Only")
        assert pm.get_preset("Music Only") is None


def test_rpyc_decompiler_fallback() -> None:
    """Tests RpycDecompiler string and AST fallback processing."""
    raw_content = b"RENPY RPC2\x00\x00\x00\x01label start:\n    'Sample dialogue line'"
    decompiled = RpycDecompiler.decompile(raw_content)

    assert "label start:" in decompiled
    assert "Sample dialogue line" in decompiled
