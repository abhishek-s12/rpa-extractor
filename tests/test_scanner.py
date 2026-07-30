"""Unit tests for directory crawling and asset category grouping logic."""

import tempfile
from pathlib import Path
from typing import Generator
import pytest
from core.scanner import AssetScanner


@pytest.fixture
def mock_game_dir() -> Generator[Path, None, None]:
    """Prepares a mock directory tree mimicking a Ren'Py game folder structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        
        # Create game folder structure
        game_sub = root / "game"
        game_sub.mkdir()

        # Place some assets
        (game_sub / "bg.png").write_bytes(b"dummy image")
        (game_sub / "bgm.mp3").write_bytes(b"dummy audio")
        (game_sub / "script.rpy").write_bytes(b"label start:\n    pass")
        (game_sub / "archive.rpa").write_bytes(b"RPA-3.0 0000000000000000 00000000\n")
        
        # Nested folders
        nested_dir = game_sub / "nested"
        nested_dir.mkdir()
        (nested_dir / "ui_font.ttf").write_bytes(b"dummy font")
        
        yield root


def test_game_folder_detection(mock_game_dir: Path) -> None:
    """Tests the detection of the 'game/' subdirectory heuristics."""
    scanner = AssetScanner(mock_game_dir)
    assert scanner.is_game_folder is True
    assert scanner.game_dir == mock_game_dir / "game"


def test_recursive_scanning_and_classification(mock_game_dir: Path) -> None:
    """Verifies that loose files are sorted into correct categories."""
    scanner = AssetScanner(mock_game_dir)
    assets = scanner.scan()

    # Verify archives list
    assert len(scanner.archives) == 1
    assert scanner.archives[0].name == "archive.rpa"

    # Verify category mappings
    assert len(assets["images"]) == 1
    assert assets["images"][0].name == "bg.png"

    assert len(assets["audio"]) == 1
    assert assets["audio"][0].name == "bgm.mp3"

    assert len(assets["scripts"]) == 1
    assert assets["scripts"][0].name == "script.rpy"

    assert len(assets["fonts"]) == 1
    assert assets["fonts"][0].name == "ui_font.ttf"


def test_selective_category_scanning(mock_game_dir: Path) -> None:
    """Checks that scanning filters work properly, returning only requested file types."""
    scanner = AssetScanner(mock_game_dir)
    
    # Scan only audio files
    assets = scanner.scan(categories=["audio"])

    # Non-audio lists must be empty
    assert len(assets["images"]) == 0
    assert len(assets["scripts"]) == 0
    assert len(assets["fonts"]) == 0

    # Audio lists must contain the asset
    assert len(assets["audio"]) == 1
    assert assets["audio"][0].name == "bgm.mp3"
