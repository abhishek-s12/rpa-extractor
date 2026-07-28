"""Audio metadata extraction module.

Uses Mutagen to parse properties like duration, bitrate, and sample rate from audio files.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, Union
import mutagen
from core.logger import logger


class AudioExtractor:
    """Extracts metadata and tracks technical properties of audio resources."""

    @staticmethod
    def get_metadata(data_or_path: Union[bytes, Path]) -> Dict[str, Any]:
        """Extracts audio specifications (duration, sample rate, bitrate, channels).

        Args:
            data_or_path: Path to the audio file or raw audio bytes.

        Returns:
            A dictionary containing audio specifications or defaults on error.
        """
        temp_file = None
        try:
            if isinstance(data_or_path, bytes):
                # Mutagen requires a filepath for full compatibility, write bytes to a tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
                    tmp.write(data_or_path)
                    tmp_path = Path(tmp.name)
                temp_file = tmp_path
                audio_file = mutagen.File(tmp_path)
            else:
                audio_file = mutagen.File(data_or_path)

            if audio_file is None or audio_file.info is None:
                return {
                    "duration": 0.0,
                    "bitrate": 0,
                    "sample_rate": 0,
                    "channels": 0,
                    "codec": "Unknown",
                }

            info = audio_file.info
            # Some info objects don't have all attributes, fetch safely
            duration = getattr(info, "length", 0.0)
            bitrate = getattr(info, "bitrate", 0)  # in bps
            sample_rate = getattr(info, "sample_rate", 0)  # in Hz
            channels = getattr(info, "channels", 0)

            # Convert bitrate to kbps
            bitrate_kbps = int(bitrate / 1000) if bitrate else 0

            # Derive codec from class name
            class_name = audio_file.__class__.__name__.lower()
            codec = "Unknown"
            if "mp3" in class_name:
                codec = "MP3"
            elif "ogg" in class_name or "vorbis" in class_name:
                codec = "Ogg Vorbis"
            elif "wave" in class_name or "wav" in class_name:
                codec = "WAV"
            elif "flac" in class_name:
                codec = "FLAC"
            elif "mp4" in class_name or "aac" in class_name:
                codec = "AAC / M4A"

            return {
                "duration": duration,
                "bitrate": bitrate_kbps,
                "sample_rate": sample_rate,
                "channels": channels,
                "codec": codec,
            }

        except Exception as e:
            logger.debug(f"Failed to read audio metadata: {e}")
            return {
                "duration": 0.0,
                "bitrate": 0,
                "sample_rate": 0,
                "channels": 0,
                "codec": "Unknown",
            }
        finally:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception as e:
                    logger.debug(f"Failed to clean up temp file {temp_file}: {e}")
