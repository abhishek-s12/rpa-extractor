"""Automated Script Translation Engine for Ren'Py (.rpy) scripts.

Parses dialogue text while preserving Ren'Py text tags (e.g. {b}, {i}, {color=...}, {w}, {p}),
speaker character definitions, and formatting options. Integrates with Google Gemini API
with automatic offline fallback mode.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from core.logger import logger


class RenpyScriptTranslator:
    """Translation pipeline for Ren'Py dialogue scripts."""

    # Ren'Py text tag pattern, e.g. {b}, {/b}, {color=#ffffff}, {w=1.5}, {p}, {nw}, {fast}
    TAG_REGEX = re.compile(r"\{[^\}]+\}")

    # Ren'Py dialogue pattern: [speaker] "dialogue string"
    DIALOGUE_REGEX = re.compile(r"^(\s*)(?:([a-zA-Z0-9_]+)\s+)?\"((?:[^\"]|\\\")*)\"(\s*(?:#.*)?)$")

    def __init__(self, api_key: Optional[str] = None, target_lang: str = "Spanish") -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.target_lang = target_lang

    def extract_and_protect_tags(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Replaces Ren'Py text tags with placeholders like __TAG_0__ for translation safety."""
        tag_map: Dict[str, str] = {}
        counter = 0

        def replacer(match: re.Match) -> str:
            nonlocal counter
            placeholder = f"__TAG_{counter}__"
            tag_map[placeholder] = match.group(0)
            counter += 1
            return placeholder

        protected_text = self.TAG_REGEX.sub(replacer, text)
        return protected_text, tag_map

    def restore_tags(self, protected_text: str, tag_map: Dict[str, str]) -> str:
        """Restores original Ren'Py text tags from placeholders."""
        restored = protected_text
        for placeholder, tag in tag_map.items():
            restored = restored.replace(placeholder, tag)
        return restored

    def translate_text(self, text: str) -> str:
        """Translates text using Gemini API if configured, or offline simulation fallback."""
        protected, tag_map = self.extract_and_protect_tags(text)

        translated_text = protected
        if self.api_key:
            try:
                translated_text = self._call_gemini_api(protected)
            except Exception as e:
                logger.warning(f"Gemini API call failed, falling back to offline mode: {e}")
                translated_text = self._offline_fallback_translate(protected)
        else:
            translated_text = self._offline_fallback_translate(protected)

        return self.restore_tags(translated_text, tag_map)

    def _call_gemini_api(self, text: str) -> str:
        """Calls Google Gemini API for translation."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = (
                f"Translate the following Ren'Py visual novel dialogue string into {self.target_lang}. "
                f"Do NOT translate or alter placeholder tokens like __TAG_0__, __TAG_1__. "
                f"Return ONLY the translated text.\n\nText: {text}"
            )
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
        except ImportError:
            logger.info("google.generativeai module not installed; using offline fallback.")
        except Exception as e:
            logger.error(f"Gemini translation error: {e}")
        return self._offline_fallback_translate(text)

    def _offline_fallback_translate(self, text: str) -> str:
        """Offline simulation fallback for testing and offline translation."""
        # Simple suffix/prefix offline tag-safe simulation for testing
        prefix_map = {
            "Spanish": "[ES] ",
            "French": "[FR] ",
            "German": "[DE] ",
            "Japanese": "[JP] ",
        }
        prefix = prefix_map.get(self.target_lang, f"[{self.target_lang[:2].upper()}] ")
        return f"{prefix}{text}"

    def translate_script_file(self, input_file: Path, output_file: Optional[Path] = None) -> Path:
        """Reads a .rpy script, translates dialogue lines, and writes translated script."""
        if output_file is None:
            output_file = input_file.parent / f"{input_file.stem}_{self.target_lang.lower()}{input_file.suffix}"

        output_file.parent.mkdir(parents=True, exist_ok=True)

        translated_lines: List[str] = []
        with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        for line in lines:
            match = self.DIALOGUE_REGEX.match(line)
            if match:
                indent, speaker, dialogue_text, trailing = match.groups()
                translated_dialogue = self.translate_text(dialogue_text)
                speaker_str = f"{speaker} " if speaker else ""
                new_line = f'{indent}{speaker_str}"{translated_dialogue}"{trailing}\n'
                translated_lines.append(new_line)
            else:
                translated_lines.append(line)

        with open(output_file, "w", encoding="utf-8") as f:
            f.writelines(translated_lines)

        logger.info(f"Translated script saved to: {output_file}")
        return output_file

    def translate_directory(self, input_dir: Path, output_dir: Path) -> List[Path]:
        """Translates all .rpy script files in a directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        results: List[Path] = []
        for rpy in input_dir.rglob("*.rpy"):
            rel = rpy.relative_to(input_dir)
            out_file = output_dir / rel
            self.translate_script_file(rpy, out_file)
            results.append(out_file)
        return results
