"""Preview UI component module.

Renders rich media previews (images, scripts, metadata panels) inside CustomTkinter.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union
import customtkinter as ctk  # type: ignore[import-untyped]
from PIL import Image, ImageTk
from core.logger import logger
from extractors.audio_extractor import AudioExtractor
from extractors.image_extractor import ImageExtractor
from extractors.video_extractor import VideoExtractor
from parsers.script_parser import ScriptParser


class PreviewPanel(ctk.CTkFrame):
    """Interactive preview slot for selected game assets."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        """Initializes the preview frame."""
        super().__init__(master, **kwargs)

        # Configure layout grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Placeholder label
        self.placeholder = ctk.CTkLabel(
            self,
            text="Select an asset to preview",
            font=ctk.CTkFont(size=14, slant="italic"),
        )
        self.placeholder.grid(row=0, column=0, sticky="nsew")

        # Active widgets track lists
        self.active_widgets: list = []

    def clear(self) -> None:
        """Removes current preview components and restores placeholder."""
        for widget in self.active_widgets:
            widget.destroy()
        self.active_widgets.clear()
        self.placeholder.grid(row=0, column=0, sticky="nsew")

    def show_image(self, data_or_path: Union[bytes, Path]) -> None:
        """Displays an image preview adjusted to panel size.

        Args:
            data_or_path: Pillow Image bytes or file path on disk.
        """
        self.clear()
        self.placeholder.grid_remove()

        try:
            # Generate thumbnail sized to fit this frame
            w, h = max(200, self.winfo_width() - 40), max(200, self.winfo_height() - 60)
            pil_img = ImageExtractor.create_thumbnail(data_or_path, (w, h))

            if pil_img:
                tk_img = ImageTk.PhotoImage(pil_img)
                lbl = ctk.CTkLabel(self, image=tk_img, text="")
                lbl.image = tk_img  # keep reference
                lbl.grid(row=0, column=0, sticky="center", padx=10, pady=10)
                self.active_widgets.append(lbl)

                # Show info label below
                meta = ImageExtractor.get_metadata(data_or_path)
                info_text = f"Format: {meta.get('format')}  |  Resolution: {meta.get('width')}x{meta.get('height')}  |  Mode: {meta.get('mode')}"
                info_lbl = ctk.CTkLabel(self, text=info_text, font=ctk.CTkFont(size=12))
                info_lbl.grid(row=1, column=0, sticky="ew", pady=(0, 10))
                self.active_widgets.append(info_lbl)
            else:
                self._show_error("Failed to load image preview.")
        except Exception as e:
            logger.error(f"Error drawing image preview: {e}")
            self._show_error("Error loading image preview.")

    def show_audio(self, data_or_path: Union[bytes, Path], filename: str) -> None:
        """Renders technical metadata specifications for audio.

        Args:
            data_or_path: Raw audio bytes or file path on disk.
            filename: Name of the audio resource.
        """
        self.clear()
        self.placeholder.grid_remove()

        meta = AudioExtractor.get_metadata(data_or_path)

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="center", padx=20, pady=20)
        self.active_widgets.append(frame)

        # Title / Icon
        icon_lbl = ctk.CTkLabel(frame, text="🎵", font=ctk.CTkFont(size=48))
        icon_lbl.pack(pady=10)

        name_lbl = ctk.CTkLabel(
            frame,
            text=filename,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=350,
        )
        name_lbl.pack(pady=5)

        # Metadata specifications table
        duration_sec = meta.get("duration", 0.0)
        minutes = int(duration_sec // 60)
        seconds = int(duration_sec % 60)
        duration_str = f"{minutes:02d}:{seconds:02d}"

        specs = [
            ("Format / Codec", meta.get("codec")),
            ("Duration", duration_str),
            ("Bitrate", f"{meta.get('bitrate')} kbps"),
            ("Sample Rate", f"{meta.get('sample_rate')} Hz"),
            ("Channels", "Stereo" if meta.get("channels") == 2 else "Mono" if meta.get("channels") == 1 else str(meta.get("channels"))),
        ]

        for label, val in specs:
            row_frame = ctk.CTkFrame(frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)

            lbl_w = ctk.CTkLabel(
                row_frame,
                text=f"{label}:",
                anchor="w",
                font=ctk.CTkFont(size=12, weight="bold"),
                width=120,
            )
            lbl_w.pack(side="left")

            val_w = ctk.CTkLabel(row_frame, text=str(val), anchor="w", font=ctk.CTkFont(size=12))
            val_w.pack(side="left", padx=10)

    def show_video(self, data_or_path: Union[bytes, Path], filename: str) -> None:
        """Renders technical metadata specifications for video.

        Args:
            data_or_path: Raw video bytes or file path on disk.
            filename: Name of the video resource.
        """
        self.clear()
        self.placeholder.grid_remove()

        meta = VideoExtractor.get_metadata(data_or_path)

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="center", padx=20, pady=20)
        self.active_widgets.append(frame)

        # Icon
        icon_lbl = ctk.CTkLabel(frame, text="🎬", font=ctk.CTkFont(size=48))
        icon_lbl.pack(pady=10)

        name_lbl = ctk.CTkLabel(
            frame,
            text=filename,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=350,
        )
        name_lbl.pack(pady=5)

        # Specifications table
        duration_sec = meta.get("duration", 0.0)
        minutes = int(duration_sec // 60)
        seconds = int(duration_sec % 60)
        duration_str = f"{minutes:02d}:{seconds:02d}"

        specs = [
            ("Resolution", f"{meta.get('width')}x{meta.get('height')}"),
            ("Framerate", f"{meta.get('fps'):.2f} FPS"),
            ("Frames Count", str(meta.get("frame_count"))),
            ("Duration", duration_str),
        ]

        for label, val in specs:
            row_frame = ctk.CTkFrame(frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)

            lbl_w = ctk.CTkLabel(
                row_frame,
                text=f"{label}:",
                anchor="w",
                font=ctk.CTkFont(size=12, weight="bold"),
                width=120,
            )
            lbl_w.pack(side="left")

            val_w = ctk.CTkLabel(row_frame, text=str(val), anchor="w", font=ctk.CTkFont(size=12))
            val_w.pack(side="left", padx=10)

    def show_script(self, data_or_path: Union[bytes, Path], filename: str) -> None:
        """Renders script analysis metrics and leading lines preview.

        Args:
            data_or_path: Script contents bytes or path.
            filename: Script filename.
        """
        self.clear()
        self.placeholder.grid_remove()

        meta = ScriptParser.parse_script(data_or_path)

        # Layout divides into top metrics panel and bottom text preview box
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        metrics_frame = ctk.CTkFrame(self)
        metrics_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.active_widgets.append(metrics_frame)

        # Details display in grid layout
        details = [
            ("Total Lines", meta.get("total_lines")),
            ("Comments", meta.get("comment_count")),
            ("Dialogue lines", meta.get("dialogue_count")),
            ("Labels count", meta.get("label_count")),
        ]

        for i, (label, val) in enumerate(details):
            metrics_frame.grid_columnconfigure(i, weight=1)
            lbl = ctk.CTkLabel(
                metrics_frame,
                text=f"{label}\n{val}",
                font=ctk.CTkFont(size=11),
                justify="center",
            )
            lbl.grid(row=0, column=i, padx=5, pady=5)

        # Read first 100 lines for the textbox preview
        try:
            if isinstance(data_or_path, Path):
                with open(data_or_path, "r", encoding="utf-8", errors="ignore") as f:
                    preview_lines = [f.readline() for _ in range(100)]
            else:
                lines = data_or_path.decode("utf-8", errors="ignore").splitlines()
                preview_lines = [l + "\n" for l in lines[:100]]
            preview_text = "".join(preview_lines)
        except Exception:
            preview_text = "Failed to load script content preview."

        tb = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=11))
        tb.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tb.insert("1.0", preview_text)
        tb.configure(state="disabled")
        self.active_widgets.append(tb)

    def show_text(self, data_or_path: Union[bytes, Path], filename: str) -> None:
        """Displays raw text contents in a textbox.

        Args:
            data_or_path: File bytes or path.
            filename: File name.
        """
        self.clear()
        self.placeholder.grid_remove()

        try:
            if isinstance(data_or_path, Path):
                with open(data_or_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read(5000)  # Read up to 5k chars
            else:
                text = data_or_path.decode("utf-8", errors="ignore")[:5000]
        except Exception:
            text = "Failed to load text preview."

        tb = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=11))
        tb.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        tb.insert("1.0", text)
        tb.configure(state="disabled")
        self.active_widgets.append(tb)

    def _show_error(self, message: str) -> None:
        """Draws an error message onto the center of the panel."""
        lbl = ctk.CTkLabel(
            self,
            text=message,
            text_color="red",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        lbl.grid(row=0, column=0, sticky="center")
        self.active_widgets.append(lbl)
