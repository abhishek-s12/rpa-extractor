"""Preview UI component module.

Renders rich media previews (images, scripts, metadata panels) and handles live audio/video playback inside CustomTkinter.
"""

import sys
import os
import tempfile
import math
import hashlib
import cv2
import ctypes
from pathlib import Path
from typing import Any, Dict, Optional, Union, cast
import customtkinter as ctk  # type: ignore[import-untyped]
from PIL import Image, ImageTk
from core.logger import logger
from extractors.audio_extractor import AudioExtractor
from extractors.image_extractor import ImageExtractor
from extractors.video_extractor import VideoExtractor
from parsers.script_parser import ScriptParser


class PreviewPanel(ctk.CTkFrame):
    """Interactive preview slot for selected game assets with media playback."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        """Initializes the preview frame and sets up playback states."""
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

        # Active widgets list tracking
        self.active_widgets: list = []

        # Audio Player State
        self.audio_alias = "rpa_mci_audio"
        self.audio_playing = False
        self.audio_temp_path: Optional[str] = None
        self.audio_data_or_path: Optional[Union[bytes, Path]] = None

        # Video Player State
        self.video_cap: Optional[cv2.VideoCapture] = None
        self.video_playing = False
        self.video_fps = 30.0
        self.video_temp_path: Optional[str] = None
        self.video_canvas: Optional[ctk.CTkCanvas] = None
        self.tk_frame_photo: Optional[ImageTk.PhotoImage] = None

    def clear(self) -> None:
        """Stops active media playbacks and clears widgets."""
        self.stop_audio()
        self.stop_video()

        # Destroy widgets
        for widget in self.active_widgets:
            try:
                widget.destroy()
            except Exception:
                pass
        self.active_widgets.clear()

        # Reset grid config to defaults
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self.placeholder.grid(row=0, column=0, sticky="nsew")

    # ==========================================
    # Audio Playback Engine
    # ==========================================
    def play_audio(self) -> None:
        """Starts audio playback using Windows MCI calls."""
        if not self.audio_data_or_path:
            return

        if sys.platform != "win32":
            logger.warning("Audio playback is only supported on Windows.")
            return

        # Prepare path
        if isinstance(self.audio_data_or_path, bytes):
            if not self.audio_temp_path:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                    tmp.write(self.audio_data_or_path)
                    self.audio_temp_path = tmp.name
            path_str = self.audio_temp_path
        else:
            path_str = str(self.audio_data_or_path)

        try:
            # Stop first if playing
            if self.audio_playing:
                ctypes.windll.winmm.mciSendStringW(f"stop {self.audio_alias}", None, 0, 0)
                ctypes.windll.winmm.mciSendStringW(f"close {self.audio_alias}", None, 0, 0)

            # Open alias
            cmd = f'open "{path_str}" type mpegvideo alias {self.audio_alias}'
            res = ctypes.windll.winmm.mciSendStringW(cmd, None, 0, 0)
            if res == 0:
                ctypes.windll.winmm.mciSendStringW(f"play {self.audio_alias}", None, 0, 0)
                self.audio_playing = True
                audio_ref = cast(Union[bytes, Path], self.audio_data_or_path)
                logger.info(f"Playback started: {filename_from_path(audio_ref)}")
            else:
                logger.error(f"MCI failed to open audio (Error code {res})")
        except Exception as e:
            logger.error(f"Error starting audio: {e}")

    def pause_audio(self) -> None:
        """Pauses the current audio playback."""
        if sys.platform == "win32" and self.audio_playing:
            try:
                ctypes.windll.winmm.mciSendStringW(f"pause {self.audio_alias}", None, 0, 0)
                self.audio_playing = False
                logger.debug("Audio playback paused.")
            except Exception as e:
                logger.error(f"MCI pause error: {e}")

    def stop_audio(self) -> None:
        """Stops and closes the current audio device session."""
        if sys.platform == "win32" and (self.audio_playing or self.audio_temp_path):
            try:
                ctypes.windll.winmm.mciSendStringW(f"stop {self.audio_alias}", None, 0, 0)
                ctypes.windll.winmm.mciSendStringW(f"close {self.audio_alias}", None, 0, 0)
            except Exception as e:
                logger.debug(f"MCI stop error: {e}")
        self.audio_playing = False
        self.audio_data_or_path = None
        if self.audio_temp_path and os.path.exists(self.audio_temp_path):
            try:
                os.unlink(self.audio_temp_path)
            except Exception:
                pass
            self.audio_temp_path = None

    def draw_waveform(self, canvas: Any, filename: str) -> None:
        """Draws a procedurally deterministic waveform based on the filename hash."""
        canvas.update()
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10 or h < 10:
            w, h = 320, 80

        h_val = int(hashlib.md5(filename.encode("utf-8")).hexdigest(), 16)

        bar_count = 50
        spacing = 3
        bar_width = max(2, int((w - (bar_count * spacing) - 30) / bar_count))

        canvas.delete("all")
        for i in range(bar_count):
            phase = (h_val >> (i % 32)) & 0xFF
            val = abs(math.sin(i * 0.15 + phase) * 0.6) + abs(math.sin(i * 0.05) * 0.4)
            bar_h = int(val * (h * 0.85))
            y0 = int((h - bar_h) / 2)
            y1 = y0 + bar_h
            x0 = i * (bar_width + spacing) + 15
            x1 = x0 + bar_width

            canvas.create_rectangle(x0, y0, x1, y1, fill="#1f538d", outline="")

    # ==========================================
    # Video Playback Engine
    # ==========================================
    def start_video_playback(self, data_or_path: Union[bytes, Path]) -> None:
        """Initializes OpenCV Video Capture and starts the frame draw loop."""
        self.stop_video()

        if isinstance(data_or_path, bytes):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
                tmp.write(data_or_path)
                self.video_temp_path = tmp.name
            path_str = self.video_temp_path
        else:
            path_str = str(data_or_path)

        self.video_cap = cv2.VideoCapture(path_str)
        if not self.video_cap.isOpened():
            logger.error("Failed to initialize video capture stream.")
            return

        self.video_fps = self.video_cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.video_playing = True
        logger.info(f"Video playback started: {filename_from_path(data_or_path)}")
        self._video_loop_step()

    def _video_loop_step(self) -> None:
        """Reads frame and updates canvas dynamically at the target FPS."""
        if not self.video_playing or self.video_cap is None or self.video_canvas is None:
            return

        ret, frame = self.video_cap.read()
        if ret:
            try:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.video_canvas.update()
                cw = self.video_canvas.winfo_width() or 320
                ch = self.video_canvas.winfo_height() or 180

                # Scale frame to fit canvas
                img = Image.fromarray(frame_rgb)
                img.thumbnail((cw, ch), Image.Resampling.BILINEAR)

                self.tk_frame_photo = ImageTk.PhotoImage(img)
                self.video_canvas.delete("all")
                self.video_canvas.create_image(cw / 2, ch / 2, image=self.tk_frame_photo, anchor="center")

                # Schedule next frame draw
                ms = int(1000 / self.video_fps)
                self.after(ms, self._video_loop_step)
            except Exception as e:
                logger.error(f"Error drawing video frame: {e}")
                self.stop_video()
        else:
            # End of video
            self.stop_video()

    def stop_video(self) -> None:
        """Releases the OpenCV video capture handle."""
        self.video_playing = False
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
        if self.video_temp_path and os.path.exists(self.video_temp_path):
            try:
                os.unlink(self.video_temp_path)
            except Exception:
                pass
            self.video_temp_path = None
        logger.debug("Video playback stopped.")

    # ==========================================
    # Preview Renderers
    # ==========================================
    def show_image(self, data_or_path: Union[bytes, Path]) -> None:
        """Displays an image preview adjusted to panel size."""
        self.clear()
        self.placeholder.grid_remove()

        try:
            w, h = max(200, self.winfo_width() - 40), max(200, self.winfo_height() - 60)
            pil_img = ImageExtractor.create_thumbnail(data_or_path, (w, h))

            if pil_img:
                tk_img = ImageTk.PhotoImage(pil_img)
                lbl = ctk.CTkLabel(self, image=tk_img, text="")
                lbl.image = tk_img
                lbl.grid(row=0, column=0, sticky="center", padx=10, pady=10)
                self.active_widgets.append(lbl)

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
        """Renders the audio specs alongside Play/Pause controls and a Waveform Canvas."""
        self.clear()
        self.placeholder.grid_remove()

        self.audio_data_or_path = data_or_path
        meta = AudioExtractor.get_metadata(data_or_path)

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="center", padx=20, pady=20)
        self.active_widgets.append(frame)

        # Title
        name_lbl = ctk.CTkLabel(
            frame,
            text=filename,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=350,
        )
        name_lbl.pack(pady=5)

        # Waveform Canvas
        canvas = ctk.CTkCanvas(frame, height=80, width=320, bg="#1a1a1a", highlightthickness=0)
        canvas.pack(pady=10)
        self.draw_waveform(canvas, filename)
        self.active_widgets.append(canvas)

        # Player Controls Buttons
        ctrl_frame = ctk.CTkFrame(frame, fg_color="transparent")
        ctrl_frame.pack(pady=5)

        play_btn = ctk.CTkButton(
            ctrl_frame, text="▶ Play", width=70, command=self.play_audio, fg_color="#38a169", hover_color="#2f855a"
        )
        play_btn.pack(side="left", padx=5)

        pause_btn = ctk.CTkButton(
            ctrl_frame, text="⏸ Pause", width=70, command=self.pause_audio, fg_color="#d69e2e", hover_color="#b7791f"
        )
        pause_btn.pack(side="left", padx=5)

        stop_btn = ctk.CTkButton(
            ctrl_frame, text="⏹ Stop", width=70, command=self.stop_audio, fg_color="#e53e3e", hover_color="#c53030"
        )
        stop_btn.pack(side="left", padx=5)

        # Metadata specifications table
        duration_sec = meta.get("duration", 0.0)
        minutes = int(duration_sec // 60)
        seconds = int(duration_sec % 60)
        duration_str = f"{minutes:02d}:{seconds:02d}"

        specs = [
            ("Codec", meta.get("codec")),
            ("Duration", duration_str),
            ("Bitrate", f"{meta.get('bitrate')} kbps"),
            ("Sample Rate", f"{meta.get('sample_rate')} Hz"),
        ]

        for label, val in specs:
            row_frame = ctk.CTkFrame(frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)

            lbl_w = ctk.CTkLabel(
                row_frame,
                text=f"{label}:",
                anchor="w",
                font=ctk.CTkFont(size=12, weight="bold"),
                width=100,
            )
            lbl_w.pack(side="left")

            val_w = ctk.CTkLabel(row_frame, text=str(val), anchor="w", font=ctk.CTkFont(size=12))
            val_w.pack(side="left", padx=10)

    def show_video(self, data_or_path: Union[bytes, Path], filename: str) -> None:
        """Renders technical metadata specifications and a Video Frame Canvas player."""
        self.clear()
        self.placeholder.grid_remove()

        meta = VideoExtractor.get_metadata(data_or_path)

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="center", padx=20, pady=20)
        self.active_widgets.append(frame)

        # Title
        name_lbl = ctk.CTkLabel(
            frame,
            text=filename,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=350,
        )
        name_lbl.pack(pady=5)

        # Video Canvas
        self.video_canvas = ctk.CTkCanvas(frame, height=180, width=320, bg="#1a1a1a", highlightthickness=0)
        self.video_canvas.pack(pady=10)
        self.active_widgets.append(self.video_canvas)

        # Load first frame statically
        try:
            temp_file = None
            if isinstance(data_or_path, bytes):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
                    tmp.write(data_or_path)
                    temp_file = tmp.name
                path_str = temp_file
            else:
                path_str = str(data_or_path)

            cap = cv2.VideoCapture(path_str)
            if cap.isOpened():
                ret, static_frame = cap.read()
                if ret:
                    static_rgb = cv2.cvtColor(static_frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(static_rgb)
                    img.thumbnail((320, 180), Image.Resampling.BILINEAR)
                    self.tk_frame_photo = ImageTk.PhotoImage(img)
                    self.video_canvas.create_image(160, 90, image=self.tk_frame_photo, anchor="center")
                cap.release()
            
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)
        except Exception as e:
            logger.debug(f"Could not load static first frame: {e}")

        # Controls Buttons
        ctrl_frame = ctk.CTkFrame(frame, fg_color="transparent")
        ctrl_frame.pack(pady=5)

        play_btn = ctk.CTkButton(
            ctrl_frame,
            text="▶ Play Video",
            width=100,
            command=lambda: self.start_video_playback(data_or_path),
            fg_color="#38a169",
            hover_color="#2f855a",
        )
        play_btn.pack(side="left", padx=5)

        stop_btn = ctk.CTkButton(
            ctrl_frame, text="⏹ Stop", width=70, command=self.stop_video, fg_color="#e53e3e", hover_color="#c53030"
        )
        stop_btn.pack(side="left", padx=5)

        # Specifications table
        duration_sec = meta.get("duration", 0.0)
        minutes = int(duration_sec // 60)
        seconds = int(duration_sec % 60)
        duration_str = f"{minutes:02d}:{seconds:02d}"

        specs = [
            ("Resolution", f"{meta.get('width')}x{meta.get('height')}"),
            ("Framerate", f"{meta.get('fps'):.2f} FPS"),
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
                width=100,
            )
            lbl_w.pack(side="left")

            val_w = ctk.CTkLabel(row_frame, text=str(val), anchor="w", font=ctk.CTkFont(size=12))
            val_w.pack(side="left", padx=10)

    def show_script(self, data_or_path: Union[bytes, Path], filename: str) -> None:
        """Renders script analysis metrics and leading lines preview."""
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
        """Displays raw text contents in a textbox."""
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


def filename_from_path(data_or_path: Union[bytes, Path]) -> str:
    """Extracts base filename from Path or returns raw labels."""
    if isinstance(data_or_path, Path):
        return data_or_path.name
    return "In-Memory Bytes"
