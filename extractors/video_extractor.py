"""Video metadata extraction module.

Uses OpenCV to inspect properties like frame resolution, FPS, and running length.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, Union
import cv2
from core.logger import logger


class VideoExtractor:
    """Extracts metadata and tracks technical properties of video resources."""

    @staticmethod
    def get_metadata(data_or_path: Union[bytes, Path]) -> Dict[str, Any]:
        """Extracts video details (width, height, fps, frame count, duration).

        Args:
            data_or_path: Path to the video file or raw video bytes.

        Returns:
            A dictionary containing video specifications or defaults on error.
        """
        temp_file = None
        cap = None
        try:
            if isinstance(data_or_path, bytes):
                # OpenCV requires a filepath for VideoCapture, write bytes to a tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
                    tmp.write(data_or_path)
                    tmp_path = Path(tmp.name)
                temp_file = tmp_path
                video_path_str = str(tmp_path)
            else:
                video_path_str = str(data_or_path)

            cap = cv2.VideoCapture(video_path_str)
            if not cap.isOpened():
                return {
                    "width": 0,
                    "height": 0,
                    "fps": 0.0,
                    "frame_count": 0,
                    "duration": 0.0,
                }

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Calculate duration
            duration = 0.0
            if fps > 0:
                duration = frame_count / fps

            return {
                "width": width,
                "height": height,
                "fps": fps,
                "frame_count": frame_count,
                "duration": duration,
            }

        except Exception as e:
            logger.debug(f"Failed to read video metadata: {e}")
            return {
                "width": 0,
                "height": 0,
                "fps": 0.0,
                "frame_count": 0,
                "duration": 0.0,
            }
        finally:
            if cap:
                cap.release()
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception as e:
                    logger.debug(f"Failed to clean up temp file {temp_file}: {e}")
