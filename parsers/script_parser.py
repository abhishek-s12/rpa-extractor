"""Script parser for Ren'Py (.rpy) files.

Scans dialogues, labels, and definitions to provide metadata reports of script assets.
"""

from pathlib import Path
from typing import Any, Dict, List, Union
from core.logger import logger


class ScriptParser:
    """Parses Ren'Py script files to analyze contents and statistics."""

    @staticmethod
    def parse_script(data_or_path: Union[bytes, Path]) -> Dict[str, Any]:
        """Parses a Ren'Py script file and aggregates code/dialogue statistics.

        Args:
            data_or_path: Path to the .rpy file or raw bytes content.

        Returns:
            A metadata dictionary containing label lists, counts, and comments.
        """
        try:
            if isinstance(data_or_path, Path):
                with open(data_or_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            else:
                content = data_or_path.decode("utf-8", errors="ignore")

            lines = content.splitlines()

            total_lines = len(lines)
            comment_count = 0
            label_count = 0
            definition_count = 0
            dialogue_count = 0
            labels: List[str] = []

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue

                # Count comments
                if stripped.startswith("#"):
                    comment_count += 1
                    continue

                # Count labels
                if stripped.startswith("label ") and stripped.endswith(":"):
                    label_name = stripped[6:-1].strip()
                    labels.append(label_name)
                    label_count += 1
                    continue

                # Count definitions
                if stripped.startswith("define ") or stripped.startswith("default "):
                    definition_count += 1
                    continue

                # Simple dialogue heuristic: character_name "speech text" or "speech text"
                # Exclude lines starting with keywords
                keywords = ("label", "define", "default", "show", "hide", "image", "play", "stop", "jump", "call", "scene", "if", "else", "menu", "return", "pass")
                if not stripped.startswith(keywords):
                    # Check for quote marks suggesting dialogue
                    if ('"' in stripped or "'" in stripped) and not stripped.startswith("$"):
                        dialogue_count += 1

            return {
                "total_lines": total_lines,
                "comment_count": comment_count,
                "label_count": label_count,
                "definition_count": definition_count,
                "dialogue_count": dialogue_count,
                "labels": labels[:50],  # Limit to first 50 labels to keep metadata clean
            }

        except Exception as e:
            logger.debug(f"Failed to parse script: {e}")
            return {
                "total_lines": 0,
                "comment_count": 0,
                "label_count": 0,
                "definition_count": 0,
                "dialogue_count": 0,
                "labels": [],
            }
