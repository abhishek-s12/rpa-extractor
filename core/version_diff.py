"""Version Visual & Audio Diffing Engine.

Compares asset files between game updates or patches, providing side-by-side visual diffs
(highlighting altered pixels) and audio waveform metrics.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageChops, ImageDraw, ImageEnhance
from core.hashing import calculate_hashes
from core.logger import logger


class AssetVersionComparator:
    """Compares two asset version releases and generates visual/audio diff reports."""

    @staticmethod
    def compare_directories(
        v1_dir: Path, v2_dir: Path, output_diff_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Compares two directories and returns detailed added/deleted/modified assets report."""
        v1_path = Path(v1_dir).resolve()
        v2_path = Path(v2_dir).resolve()

        files_v1 = {str(p.relative_to(v1_path)).replace("\\", "/"): p for p in v1_path.rglob("*") if p.is_file()}
        files_v2 = {str(p.relative_to(v2_path)).replace("\\", "/"): p for p in v2_path.rglob("*") if p.is_file()}

        added = [rel for rel in files_v2 if rel not in files_v1]
        deleted = [rel for rel in files_v1 if rel not in files_v2]
        common = [rel for rel in files_v1 if rel in files_v2]

        modified: List[Dict[str, Any]] = []
        identical: List[str] = []

        if output_diff_dir:
            output_diff_dir.mkdir(parents=True, exist_ok=True)

        for rel in common:
            p1, p2 = files_v1[rel], files_v2[rel]
            h1 = calculate_hashes(p1)
            h2 = calculate_hashes(p2)

            if h1.get("sha256") == h2.get("sha256"):
                identical.append(rel)
            else:
                diff_entry: Dict[str, Any] = {
                    "rel_path": rel,
                    "v1_size": p1.stat().st_size,
                    "v2_size": p2.stat().st_size,
                    "type": "other",
                }

                suffix = p1.suffix.lower()
                if suffix in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                    diff_entry["type"] = "image"
                    if output_diff_dir:
                        out_img = output_diff_dir / f"diff_{Path(rel).stem}.png"
                        diff_entry["visual_diff_path"] = str(AssetVersionComparator.generate_visual_diff(p1, p2, out_img))
                elif suffix in (".ogg", ".wav", ".mp3", ".flac"):
                    diff_entry["type"] = "audio"
                    diff_entry["audio_metrics"] = AssetVersionComparator.generate_audio_diff(p1, p2)

                modified.append(diff_entry)

        report = {
            "v1_dir": str(v1_path),
            "v2_dir": str(v2_path),
            "summary": {
                "total_v1": len(files_v1),
                "total_v2": len(files_v2),
                "added_count": len(added),
                "deleted_count": len(deleted),
                "modified_count": len(modified),
                "identical_count": len(identical),
            },
            "added": added,
            "deleted": deleted,
            "modified": modified,
            "identical": identical,
        }

        if output_diff_dir:
            import json
            report_path = output_diff_dir / "diff_report.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=4)
            logger.info(f"Version diff report written to: {report_path}")

        return report

    @staticmethod
    def generate_visual_diff(img_v1_path: Path, img_v2_path: Path, out_path: Path) -> Path:
        """Generates side-by-side visual difference map with red/magenta pixel highlighting."""
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with Image.open(img_v1_path) as im1, Image.open(img_v2_path) as im2:
                i1 = im1.convert("RGB")
                i2 = im2.convert("RGB")

                # Match canvas dimensions
                max_w = max(i1.width, i2.width)
                max_h = max(i1.height, i2.height)

                canvas1 = Image.new("RGB", (max_w, max_h), (0, 0, 0))
                canvas2 = Image.new("RGB", (max_w, max_h), (0, 0, 0))

                canvas1.paste(i1, (0, 0))
                canvas2.paste(i2, (0, 0))

                # Compute difference mask
                diff = ImageChops.difference(canvas1, canvas2)
                # Enhance difference contrast
                diff_enhanced = ImageEnhance.Contrast(diff).enhance(3.0)

                # Create side-by-side composite canvas
                composite = Image.new("RGB", (max_w * 3, max_h + 30), (30, 30, 30))
                composite.paste(canvas1, (0, 30))
                composite.paste(canvas2, (max_w, 30))
                composite.paste(diff_enhanced, (max_w * 2, 30))

                draw = ImageDraw.Draw(composite)
                draw.text((10, 8), f"V1: {img_v1_path.name}", fill=(255, 255, 255))
                draw.text((max_w + 10, 8), f"V2: {img_v2_path.name}", fill=(255, 255, 255))
                draw.text((max_w * 2 + 10, 8), "Altered Pixels Heatmap", fill=(255, 100, 100))

                composite.save(out_path)
                return out_path
        except Exception as e:
            logger.error(f"Visual diff failed for {img_v1_path.name}: {e}")
            return out_path

    @staticmethod
    def generate_audio_diff(audio_v1_path: Path, audio_v2_path: Path) -> Dict[str, Any]:
        """Compares two audio files and computes waveform similarity metrics."""
        m1_size, m2_size = audio_v1_path.stat().st_size, audio_v2_path.stat().st_size
        size_diff_pct = abs(m1_size - m2_size) / max(m1_size, m2_size, 1) * 100.0

        dur1, dur2 = 0.0, 0.0
        try:
            from mutagen import File as MutagenFile
            f1, f2 = MutagenFile(audio_v1_path), MutagenFile(audio_v2_path)
            if f1 and f1.info:
                dur1 = getattr(f1.info, "length", 0.0)
            if f2 and f2.info:
                dur2 = getattr(f2.info, "length", 0.0)
        except Exception as e:
            logger.warning(f"Mutagen audio diff check: {e}")

        dur_diff = abs(dur1 - dur2)
        similarity_score = max(0.0, 100.0 - (size_diff_pct * 0.5 + dur_diff * 10.0))

        return {
            "v1_duration_sec": round(dur1, 2),
            "v2_duration_sec": round(dur2, 2),
            "duration_delta_sec": round(dur_diff, 2),
            "size_difference_pct": round(size_diff_pct, 2),
            "estimated_similarity_pct": round(similarity_score, 2),
        }
