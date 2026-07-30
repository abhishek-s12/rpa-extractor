"""Real-Time Video Player with Overlay HUD.

Overlays resolution, framerate, and current time indices dynamically on the video canvas during playback.
"""

from pathlib import Path
from typing import Optional, Union
import cv2
from PySide6.QtCore import QTime, QTimer, QUrl, Qt
from PySide6.QtGui import QColor, QFont, QImage, QKeyEvent, QPaintEvent, QPainter, QPen, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget
from core.logger import logger


class VideoCanvasWithHUD(QLabel):
    """Video canvas displaying frame images with real-time HUD metrics overlay."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #000000; border-radius: 6px;")

        # HUD State
        self.resolution_str = "N/A"
        self.fps_str = "0 FPS"
        self.current_time_str = "00:00.00"
        self.frame_index = 0
        self.total_frames = 0
        self.hud_visible = True

    def set_hud_metrics(self, width: int, height: int, fps: float, current_ms: int, frame_idx: int, total_frames: int) -> None:
        self.resolution_str = f"{width}x{height}"
        self.fps_str = f"{fps:.1f} FPS"
        self.frame_index = frame_idx
        self.total_frames = total_frames
        self.current_time_str = QTime(0, 0, 0).addMSecs(current_ms).toString("mm:ss.z")[:8]
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)

        if not self.hud_visible:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw HUD overlay banner top-left
        hud_rect_x, hud_rect_y = 12, 12
        hud_w, hud_h = 210, 85

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(15, 17, 23, 200))  # Semi-transparent dark glassmorphism
        painter.drawRoundedRect(hud_rect_x, hud_rect_y, hud_w, hud_h, 6, 6)

        painter.setPen(QPen(QColor("#3b82f6"), 1))
        painter.drawRoundedRect(hud_rect_x, hud_rect_y, hud_w, hud_h, 6, 6)

        # Text
        painter.setFont(QFont("Consolas", 10, QFont.Bold))
        painter.setPen(QColor("#38bdf8"))  # Cyan header
        painter.drawText(hud_rect_x + 10, hud_rect_y + 20, "VIDEO HUD INFO")

        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor("#f8fafc"))
        painter.drawText(hud_rect_x + 10, hud_rect_y + 38, f"Res:  {self.resolution_str}")
        painter.drawText(hud_rect_x + 10, hud_rect_y + 54, f"Rate: {self.fps_str}")
        painter.drawText(hud_rect_x + 10, hud_rect_y + 70, f"Time: {self.current_time_str} ({self.frame_index}/{self.total_frames})")


class InteractiveVideoPlayer(QWidget):
    """Complete video player with dynamic HUD overlay and OpenCV playback fallback."""

    SEEK_STEP_SECONDS = 5

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.video_path: Optional[Path] = None
        self.cap: Optional[cv2.VideoCapture] = None

        self.width = 0
        self.height = 0
        self.fps = 30.0
        self.total_frames = 0
        self.current_frame = 0
        self.is_playing = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._read_next_frame)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Title
        self.title_label = QLabel("No Video Loaded")
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(self.title_label)

        # Video Canvas with HUD
        self.canvas = VideoCanvasWithHUD()
        layout.addWidget(self.canvas, 1)

        # Seek Bar & Controls
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 100)
        self.seek_slider.sliderMoved.connect(self._seek_frame)
        layout.addWidget(self.seek_slider)

        ctrl_layout = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.play_btn.setMinimumWidth(80)
        self.play_btn.clicked.connect(self.toggle_play)

        self.hud_btn = QPushButton("Toggle HUD")
        self.hud_btn.setObjectName("SecondaryBtn")
        self.hud_btn.clicked.connect(self.toggle_hud)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: #94a3b8;")

        ctrl_layout.addWidget(self.play_btn)
        ctrl_layout.addWidget(self.hud_btn)
        ctrl_layout.addWidget(self.time_label)
        ctrl_layout.addStretch()

        layout.addLayout(ctrl_layout)

    def load_video(self, file_path: Union[str, Path]) -> None:
        self.stop()
        self.video_path = Path(file_path).resolve()
        self.title_label.setText(self.video_path.name)

        self.cap = cv2.VideoCapture(str(self.video_path))
        if not self.cap.isOpened():
            logger.error(f"Failed to open video file: {self.video_path}")
            return

        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps_val = self.cap.get(cv2.CAP_PROP_FPS)
        self.fps = fps_val if fps_val > 0 else 30.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self.seek_slider.setRange(0, max(1, self.total_frames - 1))
        self.seek_slider.setValue(0)
        self.current_frame = 0

        # Read first frame
        self._read_next_frame()

    def toggle_play(self) -> None:
        if self.is_playing:
            self.stop()
        else:
            if not self.cap or not self.cap.isOpened():
                return
            self.is_playing = True
            self.play_btn.setText("Pause")
            interval_ms = max(10, int(1000.0 / self.fps))
            self.timer.start(interval_ms)

    def stop(self) -> None:
        self.is_playing = False
        self.timer.stop()
        self.play_btn.setText("Play")

    def toggle_hud(self) -> None:
        self.canvas.hud_visible = not self.canvas.hud_visible
        self.canvas.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Space:
            self.toggle_play()
        elif event.key() == Qt.Key_Left:
            self.seek_relative(-self.SEEK_STEP_SECONDS)
        elif event.key() == Qt.Key_Right:
            self.seek_relative(self.SEEK_STEP_SECONDS)
        else:
            super().keyPressEvent(event)

    def seek_relative(self, offset_seconds: int) -> None:
        if not self.cap or not self.cap.isOpened() or self.total_frames <= 0:
            return
        offset_frames = int(offset_seconds * self.fps)
        max_frame = self.total_frames - 1
        target_frame = max(0, min(max_frame, self.current_frame + offset_frames))
        self.seek_slider.setValue(target_frame)
        self._seek_frame(target_frame)

    def _read_next_frame(self) -> None:
        if not self.cap or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret:
            # Loop video
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.current_frame = 0
            ret, frame = self.cap.read()
            if not ret:
                self.stop()
                return

        self.current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        self.seek_slider.setValue(self.current_frame)

        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(self.canvas.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.canvas.setPixmap(scaled_pixmap)

        current_ms = int((self.current_frame / self.fps) * 1000)
        self.canvas.set_hud_metrics(self.width, self.height, self.fps, current_ms, self.current_frame, self.total_frames)

        curr_time = QTime(0, 0, 0).addMSecs(current_ms).toString("mm:ss")
        total_ms = int((self.total_frames / self.fps) * 1000)
        tot_time = QTime(0, 0, 0).addMSecs(total_ms).toString("mm:ss")
        self.time_label.setText(f"{curr_time} / {tot_time}")

    def _seek_frame(self, frame_idx: int) -> None:
        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            self._read_next_frame()
