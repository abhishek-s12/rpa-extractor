"""Thumbnail caching and rendering helper module.

Manages loading PIL images, generating thumbnails, and caching Tkinter PhotoImages.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple, Union
from PIL import Image, ImageTk
from core.logger import logger
from extractors.image_extractor import ImageExtractor


class ThumbnailManager:
    """Manages creation and caching of Tkinter-compatible thumbnails."""

    def __init__(self) -> None:
        """Initializes the manager with an empty memory cache."""
        self._cache: Dict[str, ImageTk.PhotoImage] = {}

    def get_thumbnail(
        self,
        key: str,
        data_or_path: Union[bytes, Path],
        size: Tuple[int, int] = (150, 150),
    ) -> Optional[ImageTk.PhotoImage]:
        """Fetches a thumbnail from the cache, or creates and caches it.

        Args:
            key: Unique lookup string (e.g. file path or MD5 hash).
            data_or_path: Path to the image file or raw image bytes.
            size: Size bounding box of the thumbnail.

        Returns:
            Tkinter-compatible ImageTk.PhotoImage or None if failed.
        """
        # Return cached instance if available
        cache_key = f"{key}_{size[0]}x{size[1]}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Generate a new thumbnail
        pil_img = ImageExtractor.create_thumbnail(data_or_path, size)
        if pil_img is None:
            return None

        try:
            tk_photo = ImageTk.PhotoImage(pil_img)
            self._cache[cache_key] = tk_photo
            return tk_photo
        except Exception as e:
            logger.error(f"Failed to create PhotoImage for {key}: {e}")
            return None

    def clear(self) -> None:
        """Clears all cached images from memory."""
        self._cache.clear()
        logger.debug("Thumbnail cache cleared.")
