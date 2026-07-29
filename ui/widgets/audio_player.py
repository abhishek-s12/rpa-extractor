"""Interactive Audio Player with Click-to-Seek Waveform Canvas.

Renders audio waveform data and allows clicking directly on the canvas to seek playback position.
"""

from pathlib import Path
from typing import Optional, Union
import numpy as np
from PySide6.QtCore import QPoint, QRectF, QTime, QUrl, Signal, Qt
from PySide6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPaintEvent, QPainter, QPen
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget
from core.logger import logger


class AudioWaveformCanvas(QWidget):
    """Custom canvas displaying interactive waveform with click-to-seek support."""

    seekRequested = Signal(float)  # Emits target normalized position (0.0 to 1.0)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(80)
        self.waveform_samples = np.random.uniform(0.1, 0.9, 100)
        self.current_position_ratio = 0.0

    def set_waveform_data(self, samples: np.ndarray) -> None:
        if len(samples) > 0:
            self.waveform_samples = samples
        else:
            self.waveform_samples = np.random.uniform(0.1, 0.9, 100)
        self.update()

    def set_position_ratio(self, ratio: float) -> None:
        self.current_position_ratio = max(0.0, min(1.0, ratio))
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            w = self.width()
            if w > 0:
                ratio = event.position().x() / w
                self.seekRequested.emit(ratio)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        w = rect.width()
        h = rect.height()

        # Background
        painter.fillRect(rect, QColor("#0f1117"))

        # Draw grid line
        painter.setPen(QPen(QColor("#262b38"), 1, Qt.DashLine))
        painter.drawLine(0, h // 2, w, h // 2)

        # Draw waveform bars
        n_samples = len(self.waveform_samples)
        if n_samples == 0:
            return

        bar_width = max(2.0, w / n_samples)
        playhead_x = self.current_position_ratio * w

        for i, s in enumerate(self.waveform_samples):
            x = i * bar_width
            bar_h = s * (h * 0.8)
            y_top = (h - bar_h) / 2.0

            if x <= playhead_x:
                color = QColor("#3b82f6")  # Played accent color
            else:
                color = QColor("#475569")  # Unplayed grey

            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x, y_top, max(1.0, bar_width - 1.0), bar_h), 1.5, 1.5)

        # Draw playhead bar line
        painter.setPen(QPen(QColor("#ef4444"), 2))
        painter.drawLine(int(playhead_x), 0, int(playhead_x), h)


class InteractiveAudioPlayer(QWidget):
    """Complete interactive audio player panel."""

    SEEK_STEP_MS = 5000

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        self.audio_path: Optional[Path] = None
        self.duration_ms: int = 0

        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Title / Filename Label
        self.title_label = QLabel("No Audio Loaded")
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(self.title_label)

        # Waveform Canvas
        self.waveform_canvas = AudioWaveformCanvas()
        layout.addWidget(self.waveform_canvas)

        # Controls Row
        ctrl_layout = QHBoxLayout()

        self.play_btn = QPushButton("Play")
        self.play_btn.setMinimumWidth(80)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: #94a3b8;")

        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(70)
        self.audio_output.setVolume(0.7)
        self.vol_slider.setMaximumWidth(120)

        vol_icon = QLabel("Vol:")
        vol_icon.setStyleSheet("color: #94a3b8;")

        ctrl_layout.addWidget(self.play_btn)
        ctrl_layout.addWidget(self.time_label)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(vol_icon)
        ctrl_layout.addWidget(self.vol_slider)

        layout.addLayout(ctrl_layout)

    def _connect_signals(self) -> None:
        self.play_btn.clicked.connect(self.toggle_play)
        self.waveform_canvas.seekRequested.connect(self.seek_to_ratio)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.vol_slider.valueChanged.connect(lambda v: self.audio_output.setVolume(v / 100.0))

    def load_audio(self, file_path: Union[str, Path]) -> None:
        self.audio_path = Path(file_path).resolve()
        self.title_label.setText(self.audio_path.name)
        self.media_player.setSource(QUrl.fromLocalFile(str(self.audio_path)))

        # Generate fake or sampled waveform visualization from filename/hash
        seed = sum(ord(c) for c in self.audio_path.name) % 1000
        np.random.seed(seed)
        samples = np.random.uniform(0.15, 0.95, 80)
        self.waveform_canvas.set_waveform_data(samples)
        self.waveform_canvas.set_position_ratio(0.0)

    def toggle_play(self) -> None:
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_btn.setText("Play")
        else:
            self.media_player.play()
            self.play_btn.setText("Pause")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Space:
            self.toggle_play()
        elif event.key() == Qt.Key_Left:
            self.seek_relative(-self.SEEK_STEP_MS)
        elif event.key() == Qt.Key_Right:
            self.seek_relative(self.SEEK_STEP_MS)
        else:
            super().keyPressEvent(event)

    def seek_relative(self, offset_ms: int) -> None:
        if self.duration_ms <= 0:
            return
        target_pos = max(0, min(self.duration_ms, self.media_player.position() + offset_ms))
        self.media_player.setPosition(target_pos)

    def seek_to_ratio(self, ratio: float) -> None:
        if self.duration_ms > 0:
            target_pos = int(ratio * self.duration_ms)
            self.media_player.setPosition(target_pos)
            self.waveform_canvas.set_position_ratio(ratio)

    def _on_position_changed(self, pos_ms: int) -> None:
        if self.duration_ms > 0:
            ratio = pos_ms / self.duration_ms
            self.waveform_canvas.set_position_ratio(ratio)

            curr_str = QTime(0, 0, 0).addMSecs(pos_ms).toString("mm:ss")
            dur_str = QTime(0, 0, 0).addMSecs(self.duration_ms).toString("mm:ss")
            self.time_label.setText(f"{curr_str} / {dur_str}")

    def _on_duration_changed(self, dur_ms: int) -> None:
        self.duration_ms = dur_ms
