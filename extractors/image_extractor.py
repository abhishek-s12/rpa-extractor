"""Image metadata extraction and thumbnail generation module.

Uses Pillow to retrieve image specifications and generate scaled thumbnails.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
from PIL import Image
from core.logger import logger


class ImageExtractor:
    """Extracts metadata and creates thumbnails for supported image formats."""

    @staticmethod
    def get_metadata(data_or_path: Union[bytes, Path]) -> Dict[str, Any]:
        """Reads image details (format, width, height, color mode).

        Args:
            data_or_path: Path to the image file or raw image bytes.

        Returns:
            A dictionary containing image properties or empty values on failure.
        """
        try:
            if isinstance(data_or_path, Path):
                with Image.open(data_or_path) as img:
                    return {
                        "width": img.width,
                        "height": img.height,
                        "format": img.format,
                        "mode": img.mode,
                        "animated": getattr(img, "is_animated", False),
                    }
            else:
                import io
                with Image.open(io.BytesIO(data_or_path)) as img:
                    return {
                        "width": img.width,
                        "height": img.height,
                        "format": img.format,
                        "mode": img.mode,
                        "animated": getattr(img, "is_animated", False),
                    }
        except Exception as e:
            logger.debug(f"Failed to read image metadata: {e}")
            return {
                "width": 0,
                "height": 0,
                "format": "Unknown",
                "mode": "Unknown",
                "animated": False,
            }

    @staticmethod
    def create_thumbnail(
        data_or_path: Union[bytes, Path], size: Tuple[int, int] = (150, 150)
    ) -> Optional[Image.Image]:
        """Generates a Pillow Image thumbnail scaled to fit size.

        Args:
            data_or_path: Path to the image file or raw image bytes.
            size: Desired maximum (width, height) bounding box.

        Returns:
            The scaled PIL Image object or None on error.
        """
        try:
            if isinstance(data_or_path, Path):
                img = Image.open(data_or_path)
            else:
                import io
                img = Image.open(io.BytesIO(data_or_path))

            # Resize while preserving aspect ratio
            img.thumbnail(size, Image.Resampling.LANCZOS)
            return img
        except Exception as e:
            logger.debug(f"Failed to create image thumbnail: {e}")
            return None
