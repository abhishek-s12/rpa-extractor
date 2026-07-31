"""Unit test suite for Ren'Py Asset Extraction Tool v3.0 features.

Tests AI translation & tag preservation, intelligent asset tagging, live memory patching,
version visual/audio diffing, texture upscaling & media pipeline, plugin SDK, and WASM explorer.
"""

import json
from pathlib import Path
import tempfile

from PIL import Image
import pytest

from core.live_interceptor import RenPyProcessHooker
from core.plugin_sdk import BaseExtractorPlugin, PluginRegistry
from core.smart_filter import PresetManager, SmartFilterEngine
from core.version_diff import AssetVersionComparator
from extractors.image_tagger import AssetTagger, SmartMetadataIndexer
from extractors.media_pipeline import BatchTranscoder, SpriteCleaner, TextureUpscaler
from parsers.translation_engine import RenpyScriptTranslator
from web.pyodide_explorer import filter_catalog_wasm, parse_rpa_header_wasm


def test_smart_filter_v3_tokens() -> None:
    assets = [
        {
            "name": "sprite_heroine_happy.png",
            "rel_path": "images/sprite_heroine_happy.png",
            "category": "images",
            "tags": ["happy", "main_heroine", "day"],
            "character": "main_heroine",
            "expression": "happy",
            "details": {"tags": ["happy", "main_heroine"], "tags_str": "happy main_heroine"},
        },
        {
            "name": "bg_classroom_night.png",
            "rel_path": "images/bg_classroom_night.png",
            "category": "images",
            "tags": ["background", "night", "classroom"],
            "location": "classroom",
            "details": {"location": "classroom", "tags_str": "background night classroom"},
        },
    ]

    res_tag = SmartFilterEngine.filter_assets(assets, "tag:happy")
    assert len(res_tag) == 1
    assert res_tag[0]["name"] == "sprite_heroine_happy.png"

    res_char = SmartFilterEngine.filter_assets(assets, "char:main_heroine")
    assert len(res_char) == 1

    res_loc = SmartFilterEngine.filter_assets(assets, "loc:classroom")
    assert len(res_loc) == 1
    assert res_loc[0]["name"] == "bg_classroom_night.png"


def test_preset_manager_json_sync() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = Path(tmp_dir) / "presets.json"
        pm = PresetManager(storage_path=storage)
        pm.add_preset("Custom Preset", "cat:images tag:happy")

        exported = pm.export_presets_json()
        assert "Custom Preset" in exported

        pm2 = PresetManager(storage_path=Path(tmp_dir) / "presets2.json")
        pm2.import_presets_json(exported)
        assert pm2.get_preset("Custom Preset") == "cat:images tag:happy"


def test_script_translation_engine() -> None:
    translator = RenpyScriptTranslator(target_lang="Spanish")

    raw_text = "Hello {b}World{/b}! Wait {w=1.0} and see {color=#ff0000}colors{/color}."
    protected, tag_map = translator.extract_and_protect_tags(raw_text)
    assert "__TAG_0__" in protected
    assert "{b}" in tag_map.values()

    restored = translator.restore_tags(protected, tag_map)
    assert restored == raw_text

    with tempfile.TemporaryDirectory() as tmp_dir:
        script_file = Path(tmp_dir) / "script.rpy"
        with open(script_file, "w", encoding="utf-8") as f:
            f.write('label start:\n    eileen "Hello {b}Friend{/b}!"\n    "Plain dialogue line."\n')

        out_script = translator.translate_script_file(script_file)
        assert out_script.exists()
        content = out_script.read_text(encoding="utf-8")
        assert "[ES]" in content
        assert "{b}Friend{/b}" in content


def test_image_tagger_and_indexer() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        img_path = tmp_path / "bg_classroom_night.png"

        img = Image.new("RGB", (400, 300), color=(20, 20, 50))
        img.save(img_path)

        tags_info = AssetTagger.tag_image(img_path)
        assert "night" in tags_info["tags"] or "classroom" in tags_info["tags"]

        catalog = SmartMetadataIndexer.index_directory(tmp_path)
        assert "bg_classroom_night.png" in catalog
        assert "tags" in catalog["bg_classroom_night.png"]


def test_live_interceptor_and_hook() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        game_dir = Path(tmp_dir) / "MyGame"
        mod_dir = Path(tmp_dir) / "ModAssets"

        hook_file = RenPyProcessHooker.inject_rpa_override_hook(game_dir, mod_dir)
        assert hook_file.exists()
        assert "renpy.config.searchpath.insert" in hook_file.read_text(encoding="utf-8")

        removed = RenPyProcessHooker.remove_override_hook(game_dir)
        assert removed
        assert not hook_file.exists()


def test_version_diffing() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        v1_dir = Path(tmp_dir) / "v1"
        v2_dir = Path(tmp_dir) / "v2"
        out_diff = Path(tmp_dir) / "diff"
        v1_dir.mkdir()
        v2_dir.mkdir()

        # Identical file
        (v1_dir / "same.txt").write_text("hello", encoding="utf-8")
        (v2_dir / "same.txt").write_text("hello", encoding="utf-8")

        # Added & Deleted
        (v1_dir / "old.txt").write_text("deleted", encoding="utf-8")
        (v2_dir / "new.txt").write_text("added", encoding="utf-8")

        # Modified images
        img1 = Image.new("RGB", (100, 100), color=(255, 0, 0))
        img1.save(v1_dir / "sprite.png")
        img2 = Image.new("RGB", (100, 100), color=(0, 255, 0))
        img2.save(v2_dir / "sprite.png")

        report = AssetVersionComparator.compare_directories(v1_dir, v2_dir, out_diff)
        assert report["summary"]["identical_count"] == 1
        assert "new.txt" in report["added"]
        assert "old.txt" in report["deleted"]
        assert len(report["modified"]) == 1
        assert (out_diff / "diff_report.json").exists()


def test_media_pipeline() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        img_p = tmp_path / "test.png"

        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 10))
        img.save(img_p)

        upscaled_p = tmp_path / "test_2x.png"
        TextureUpscaler.upscale_image(img_p, upscaled_p, scale=2)
        assert upscaled_p.exists()
        with Image.open(upscaled_p) as up:
            assert up.size == (200, 200)

        cleaned_p = tmp_path / "test_clean.png"
        SpriteCleaner.clean_transparency(img_p, cleaned_p)
        assert cleaned_p.exists()

        out_transcode = tmp_path / "transcoded"
        stats = BatchTranscoder.transcode_directory(tmp_path, out_transcode, image_format="webp")
        assert stats["images_converted"] > 0


def test_plugin_sdk() -> None:
    class MockCustomPlugin(BaseExtractorPlugin):
        plugin_name = "MockPlugin"
        plugin_version = "1.0.0"
        author = "Tester"
        description = "Mock plugin test"

        def can_handle(self, file_path: Path, header_bytes: bytes) -> bool:
            return header_bytes.startswith(b"MOCK")

        def read_index(self, file_path: Path) -> dict:
            return {"file1.png": [(0, 10, 0x42)]}

    plugin_inst = MockCustomPlugin()
    PluginRegistry.register(plugin_inst)

    plugins = PluginRegistry.list_plugins()
    names = [p["name"] for p in plugins]
    assert "MockPlugin" in names

    match = PluginRegistry.get_plugin_for_file(Path("dummy.bin"), b"MOCK_HEADER")
    assert match is not None
    assert match.plugin_name == "MockPlugin"

    decrypted = plugin_inst.decrypt_data(b"\x00\x01\x02", key=0xFF)
    assert decrypted == b"\xFF\xFE\xFD"


def test_pyodide_wasm_explorer() -> None:
    res = parse_rpa_header_wasm(b"RPA-3.0 0000000000000000 0424b2b4")
    assert res["valid"] is True
    assert res["version"] == "RPA-3.0"

    cat_json = json.dumps({"img1.png": {"category": "images", "tags": ["happy"]}})
    filtered = filter_catalog_wasm(cat_json, "tag:happy")
    assert "img1.png" in filtered
