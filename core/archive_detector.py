"""Archive format detection module.

Reads file headers to verify if a file is a Ren'Py Archive (RPA) and identify its version.
"""

from pathlib import Path
from typing import Optional
from core.config import RPA_SIGNATURES
from core.logger import logger


class ArchiveDetector:
    """Detects Ren'Py archive formats (RPA-3.0, RPA-2.0, etc.) from headers."""

    @staticmethod
    def detect_format(file_path: Path) -> Optional[str]:
        """Reads the header of a file and matches against known signatures.

        Args:
            file_path: Path to the target file.

        Returns:
            The detected signature format string (e.g. 'RPA-3.0') or None if not an archive.
        """
        if not file_path.exists() or not file_path.is_file():
            return None

        try:
            with open(file_path, "rb") as f:
                # Read the first line or first 50 bytes (headers are small plain text lines)
                header_bytes = f.readline().strip()

            # Find matching signature in header
            for sig in RPA_SIGNATURES:
                if header_bytes.startswith(sig):
                    detected_version = sig.decode("ascii")
                    logger.debug(f"Detected archive format {detected_version} for: {file_path}")
                    return detected_version

            # Check if there is some other common pattern or custom header that is RPA-compatible
            # Ren'Py sometimes has custom headers but we focus on official ones first
            logger.debug(f"File {file_path} did not match any standard RPA signature header.")
            return None

        except Exception as e:
            logger.error(f"Error checking header signature for {file_path}: {e}")
            return None
