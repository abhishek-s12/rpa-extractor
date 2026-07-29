"""Interactive Image Inspector Widget with Zoom-to-Cursor, Pan, and Comparison Slider.

Provides image inspection controls and a side-by-side / overlay split slider
for comparing original vs. optimized images.
"""

from pathlib import Path
from typing import Optional, Union
from PySide6.QtCore import QPoint, QRectF, Signal, Qt
from PySide6.QtGui import QColor, QFont, QImage, QMouseEvent, QPaintEvent, QPainter, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget
from core.logger import logger


class ZoomableImageCanvas(QWidget):
    """Canvas supporting mouse wheel zoom-to-cursor and drag pan."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self.setMouseTracking(True)

        self.pixmap_orig: Optional[QPixmap] = None
        self.pixmap_opt: Optional[QPixmap] = None

        self.zoom_factor: float = 1.0
        self.pan_offset: QPoint = QPoint(0, 0)
        self.drag_start: QPoint = QPoint(0, 0)
        self.is_dragging: bool = False

        self.comparison_mode: bool = False
        self.split_ratio: float = 0.5  # 0.0 to 1.0

    def set_image(self, img_source: Union[str, Path, bytes, QPixmap], optimized_source: Optional[Union[str, Path, bytes, QPixmap]] = None) -> None:
        self.pixmap_orig = self._load_pixmap(img_source)
        if optimized_source is not None:
            self.pixmap_opt = self._load_pixmap(optimized_source)
            self.comparison_mode = True
        else:
            self.pixmap_opt = None
            self.comparison_mode = False

        self.reset_view()

    def _load_pixmap(self, src: Union[str, Path, bytes, QPixmap]) -> QPixmap:
        if isinstance(src, QPixmap):
            return src
        elif isinstance(src, bytes):
            pm = QPixmap()
            pm.loadFromData(src)
            return pm
        else:
            return QPixmap(str(src))

    def reset_view(self) -> None:
        self.zoom_factor = 1.0
        self.pan_offset = QPoint(0, 0)
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self.pixmap_orig or self.pixmap_orig.isNull():
            return

        angle = event.angleDelta().y()
        factor = 1.15 if angle > 0 else 0.85

        old_zoom = self.zoom_factor
        self.zoom_factor = max(0.1, min(15.0, self.zoom_factor * factor))

        # Adjust pan offset to zoom around cursor
        cursor_pos = event.position().toPoint()
        self.pan_offset = cursor_pos - (cursor_pos - self.pan_offset) * (self.zoom_factor / old_zoom)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() in (Qt.LeftButton, Qt.MiddleButton):
            self.is_dragging = True
            self.drag_start = event.pos() - self.pan_offset

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.is_dragging:
            self.pan_offset = event.pos() - self.drag_start
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() in (Qt.LeftButton, Qt.MiddleButton):
            self.is_dragging = False

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = self.rect()
        w, h = rect.width(), rect.height()

        # Checkerboard background for transparency
        painter.fillRect(rect, QColor("#12141a"))
        grid_size = 16
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1e222e"))
        for x in range(0, w, grid_size):
            for y in range(0, h, grid_size):
                if (x // grid_size + y // grid_size) % 2 == 0:
                    painter.drawRect(x, y, grid_size, grid_size)

        if not self.pixmap_orig or self.pixmap_orig.isNull():
            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(rect, Qt.AlignCenter, "No Image Selected")
            return

        # Calculate target geometry
        pw = self.pixmap_orig.width() * self.zoom_factor
        ph = self.pixmap_orig.height() * self.zoom_factor

        x0 = (w - pw) / 2.0 + self.pan_offset.x()
        y0 = (h - ph) / 2.0 + self.pan_offset.y()
        target_rect = QRectF(x0, y0, pw, ph)

        if not self.comparison_mode or not self.pixmap_opt or self.pixmap_opt.isNull():
            # Standard single image render
            painter.drawPixmap(target_rect, self.pixmap_orig, QRectF(self.pixmap_orig.rect()))
        else:
            # Comparison Split Render
            split_x = target_rect.x() + target_rect.width() * self.split_ratio

            # Draw Left (Original)
            painter.save()
            painter.setClipRect(QRectF(target_rect.x(), target_rect.y(), target_rect.width() * self.split_ratio, target_rect.height()))
            painter.drawPixmap(target_rect, self.pixmap_orig, QRectF(self.pixmap_orig.rect()))
            painter.restore()

            # Draw Right (Optimized)
            painter.save()
            painter.setClipRect(QRectF(split_x, target_rect.y(), target_rect.width() * (1.0 - self.split_ratio), target_rect.height()))
            painter.drawPixmap(target_rect, self.pixmap_opt, QRectF(self.pixmap_opt.rect()))
            painter.restore()

            # Draw Splitter Divider Line
            painter.setPen(QPen(QColor("#3b82f6"), 2))
            painter.drawLine(int(split_x), int(target_rect.y()), int(split_x), int(target_rect.y() + target_rect.height()))

            # Labels
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.setPen(QColor("#ffffff"))
            painter.drawText(int(target_rect.x() + 10), int(target_rect.y() + 25), "Original")
            painter.drawText(int(target_rect.x() + target_rect.width() - 80), int(target_rect.y() + 25), "Optimized")

        # Zoom level badge bottom-right
        badge_str = f"{int(self.zoom_factor * 100)}%"
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor("#94a3b8"))
        painter.drawText(w - 50, h - 10, badge_str)


class ImageInspector(QWidget):
    """Complete image inspector panel with side-by-side comparison slider."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header Info Row
        header = QHBoxLayout()
        self.info_lbl = QLabel("No Image Selected")
        self.info_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))

        self.reset_btn = QPushButton("Reset View")
        self.reset_btn.setObjectName("SecondaryBtn")
        self.reset_btn.clicked.connect(self._reset)

        header.addWidget(self.info_lbl)
        header.addStretch()
        header.addWidget(self.reset_btn)
        layout.addLayout(header)

        # Main Canvas
        self.canvas = ZoomableImageCanvas()
        layout.addWidget(self.canvas, 1)

        # Comparison Slider Controls (Visible when comparison_mode is True)
        self.comp_frame = QFrame()
        comp_layout = QHBoxLayout(self.comp_frame)
        comp_layout.setContentsMargins(0, 0, 0, 0)

        lbl_orig = QLabel("Original")
        lbl_orig.setStyleSheet("color: #94a3b8;")

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(50)
        self.slider.valueChanged.connect(self._on_slider_change)

        lbl_opt = QLabel("Optimized")
        lbl_opt.setStyleSheet("color: #94a3b8;")

        comp_layout.addWidget(lbl_orig)
        comp_layout.addWidget(self.slider)
        comp_layout.addWidget(lbl_opt)

        self.comp_frame.setVisible(False)
        layout.addWidget(self.comp_frame)

    def load_image(self, file_path: Union[str, Path, bytes], opt_path: Optional[Union[str, Path, bytes]] = None) -> None:
        self.canvas.set_image(file_path, opt_path)
        if isinstance(file_path, (str, Path)):
            p = Path(file_path)
            if self.canvas.pixmap_orig:
                w, h = self.canvas.pixmap_orig.width(), self.canvas.pixmap_orig.height()
                self.info_lbl.setText(f"{p.name} ({w} x {h})")
        if opt_path is not None:
            self.comp_frame.setVisible(True)
        else:
            self.comp_frame.setVisible(False)

    def _on_slider_change(self, val: int) -> None:
        self.canvas.split_ratio = val / 100.0
        self.canvas.update()

    def _reset(self) -> None:
        self.canvas.reset_view()
