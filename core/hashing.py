"""Hashing utilities for the Ren'Py Asset Extraction Tool.

Handles MD5, SHA256, and perceptual image hashing (dHash) for file deduplication.
"""

import hashlib
from pathlib import Path
from typing import Dict, Union
from PIL import Image
from core.logger import logger


def calculate_hashes(data_or_path: Union[bytes, Path]) -> Dict[str, str]:
    """Calculates MD5 and SHA256 hashes for raw bytes or a file path.

    Args:
        data_or_path: File Path or raw bytes to hash.

    Returns:
        A dictionary containing "md5" and "sha256" hex strings.
    """
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()

    if isinstance(data_or_path, Path):
        try:
            with open(data_or_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    md5.update(chunk)
                    sha256.update(chunk)
        except Exception as e:
            logger.error(f"Failed to calculate hashes for file {data_or_path}: {e}")
            return {"md5": "", "sha256": ""}
    else:
        md5.update(data_or_path)
        sha256.update(data_or_path)

    return {
        "md5": md5.hexdigest(),
        "sha256": sha256.hexdigest(),
    }


def calculate_perceptual_hash(image_path_or_bytes: Union[Path, bytes]) -> str:
    """Calculates the Difference Hash (dHash) for an image.

    dHash tracks gradients between pixels to generate a 64-bit fingerprint.

    Args:
        image_path_or_bytes: Path to the image or raw image bytes.

    Returns:
        A 16-character hexadecimal string representing the perceptual hash.
    """
    try:
        if isinstance(image_path_or_bytes, Path):
            img = Image.open(image_path_or_bytes)
        else:
            import io
            img = Image.open(io.BytesIO(image_path_or_bytes))

        # Convert to grayscale and resize to 9x8 (9 columns, 8 rows)
        # 9 cols allows us to compare 8 horizontal pairs per row (8 rows * 8 diffs = 64 bits)
        img = img.convert("L").resize((9, 8), Image.Resampling.BILINEAR)
        pixels = list(img.getdata())

        difference = []
        for row in range(8):
            for col in range(8):
                # Get index of current pixel and right neighbor
                idx_left = row * 9 + col
                idx_right = idx_left + 1
                difference.append(pixels[idx_left] > pixels[idx_right])

        # Convert boolean list to 64-bit integer, then to hex
        decimal_val = 0
        for bit in difference:
            decimal_val = (decimal_val << 1) | int(bit)

        # Pad with zeros to ensure 16 characters
        return f"{decimal_val:016x}"

    except Exception as e:
        logger.debug(f"Could not calculate perceptual hash for image: {e}")
        return ""
