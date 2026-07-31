"""Intelligent Image & Scene Tagging Module.

Uses computer vision heuristics and metadata analysis for automated tagging of character
sprites (expression, outfit, pose) and background environments (time of day, location type).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image
from core.logger import logger


class AssetTagger:
    """Analyzes visual novel graphics to detect character expressions and environment tags."""

    @staticmethod
    def tag_image(image_path: Path) -> Dict[str, Any]:
        """Extracts AI asset tags, character expression, and environment classification."""
        if not image_path.exists():
            return {
                "tags": [],
                "character": "unknown",
                "expression": "neutral",
                "location": "unknown",
                "time_of_day": "unknown",
                "tags_str": "",
            }

        tags: List[str] = []
        character = "unknown"
        expression = "neutral"
        location = "unknown"
        time_of_day = "day"

        stem = image_path.stem.lower()

        # Filename heuristics parsing (e.g. bg_classroom_night.png, sprite_heroine_happy.png)
        if "bg_" in stem or "background" in stem or "sc_" in stem:
            tags.append("background")
            if "night" in stem or "dark" in stem or "evening" in stem:
                time_of_day = "night"
                tags.append("night")
            elif "sunset" in stem or "dusk" in stem or "orange" in stem:
                time_of_day = "sunset"
                tags.append("sunset")
            else:
                time_of_day = "day"
                tags.append("day")

            if "classroom" in stem or "school" in stem:
                location = "classroom"
                tags.append("classroom")
            elif "room" in stem or "bed" in stem or "house" in stem:
                location = "bedroom"
                tags.append("bedroom")
            elif "street" in stem or "park" in stem or "city" in stem:
                location = "street"
                tags.append("street")
            else:
                location = "indoors" if "int_" in stem else "outdoors"
                tags.append(location)
        else:
            # Sprite detection
            tags.append("sprite")
            if "main" in stem or "heroine" in stem or "alice" in stem or "eileen" in stem:
                character = "main_heroine"
                tags.append("main_heroine")
            elif "hero" in stem or "protagonist" in stem:
                character = "protagonist"
                tags.append("protagonist")
            else:
                character = stem.split("_")[0] if "_" in stem else "character"
                tags.append(character)

            if "happy" in stem or "smile" in stem or "joy" in stem or "laugh" in stem:
                expression = "happy"
                tags.append("happy")
            elif "sad" in stem or "cry" in stem or "tears" in stem:
                expression = "sad"
                tags.append("sad")
            elif "angry" in stem or "mad" in stem or "frown" in stem:
                expression = "angry"
                tags.append("angry")
            elif "surprised" in stem or "shock" in stem:
                expression = "surprised"
                tags.append("surprised")
            else:
                expression = "neutral"
                tags.append("neutral")

        # Image pixel analysis using Pillow for additional verification
        try:
            with Image.open(image_path) as img:
                img = img.convert("RGB")
                w, h = img.size
                # Compute average RGB values
                stat = img.resize((1, 1)).getpixel((0, 0))
                r, g, b = stat[0], stat[1], stat[2]
                brightness = (r + g + b) / 3.0

                if brightness < 60 and "night" not in tags:
                    time_of_day = "night"
                    if "night" not in tags:
                        tags.append("night")
                elif brightness > 200 and "bright" not in tags:
                    tags.append("bright")

                if r > b + 30 and g > b + 20 and "sunset" not in tags and brightness < 180:
                    tags.append("warm_lighting")
        except Exception as e:
            logger.warning(f"Failed image pixel analysis for {image_path.name}: {e}")

        # Remove duplicates
        unique_tags = list(dict.fromkeys(tags))

        return {
            "tags": unique_tags,
            "character": character,
            "expression": expression,
            "location": location,
            "time_of_day": time_of_day,
            "tags_str": " ".join(unique_tags),
        }


class SmartMetadataIndexer:
    """Indexes asset metadata with AI tags for multi-modal search."""

    @staticmethod
    def index_directory(output_dir: Path) -> Dict[str, Any]:
        """Scans output directory, tags image files, and updates metadata.json manifest."""
        manifest_path = output_dir / "metadata.json"
        catalog: Dict[str, Any] = {}

        if manifest_path.exists():
            import json
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    catalog = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read existing metadata.json: {e}")

        updated_count = 0
        for img_file in output_dir.rglob("*.*"):
            if img_file.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".avif", ".bmp"):
                rel_path = str(img_file.relative_to(output_dir)).replace("\\", "/")
                tag_info = AssetTagger.tag_image(img_file)

                if rel_path in catalog:
                    catalog[rel_path]["tags"] = tag_info["tags"]
                    catalog[rel_path]["character"] = tag_info["character"]
                    catalog[rel_path]["expression"] = tag_info["expression"]
                    catalog[rel_path]["location"] = tag_info["location"]
                    catalog[rel_path]["details"]["tags"] = tag_info["tags"]
                    catalog[rel_path]["details"]["tags_str"] = tag_info["tags_str"]
                else:
                    catalog[rel_path] = {
                        "original_source": "standalone",
                        "size_bytes": img_file.stat().st_size,
                        "category": "images",
                        "tags": tag_info["tags"],
                        "character": tag_info["character"],
                        "expression": tag_info["expression"],
                        "location": tag_info["location"],
                        "details": {
                            "width": 0,
                            "height": 0,
                            "tags": tag_info["tags"],
                            "tags_str": tag_info["tags_str"],
                        },
                    }
                updated_count += 1

        import json
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=4)

        logger.info(f"Indexed {updated_count} image files with AI tags in {manifest_path}")
        return catalog
