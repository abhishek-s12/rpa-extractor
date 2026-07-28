"""Configuration constants for the Ren'Py Asset Extraction Tool.

This module contains hardcoded extension maps, file category classifications,
UI default constants, and signature strings.
"""

from typing import Dict, Set

# Signatures for Ren'Py archive formats
RPA_SIGNATURES: Set[bytes] = {
    b"RPA-3.0",
    b"RPA-3.2",
    b"RPA-2.0",
    b"RPA-1.0",
}

# Mapping of file categories to their corresponding extensions
SUPPORTED_EXTENSIONS: Dict[str, Set[str]] = {
    "images": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"},
    "audio": {".mp3", ".ogg", ".wav", ".flac", ".m4a", ".opus"},
    "video": {".mp4", ".webm", ".avi", ".mkv", ".mov", ".ogv"},
    "fonts": {".ttf", ".otf", ".woff", ".woff2"},
    "scripts": {".rpy", ".rpyc", ".py"},
    "data": {".json", ".xml", ".txt", ".csv", ".yaml", ".yml"},
}

# Re-mapped category folder names in the output directory
CATEGORY_FOLDERS: Dict[str, str] = {
    "images": "images",
    "audio": "audio",
    "video": "video",
    "fonts": "fonts",
    "scripts": "scripts",
    "data": "data",
    "other": "other",
}

# UI Styling Constants
DEFAULT_THEME = "dark"
WINDOW_MIN_WIDTH = 1000
WINDOW_MIN_HEIGHT = 700

# Mutagen/Codec details display maps
AUDIO_CODECS: Dict[str, str] = {
    "mp3": "MPEG Audio Layer 3 (MP3)",
    "ogg": "Ogg Vorbis (OGG)",
    "wav": "Waveform Audio File Format (WAV)",
    "flac": "Free Lossless Audio Codec (FLAC)",
    "m4a": "MPEG-4 Audio (M4A)",
    "opus": "Opus Audio (OPUS)",
}
