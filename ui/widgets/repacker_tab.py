"""RPA Archive Compiler / Repacker GUI Tab.

Allows modders to select a folder of customized files and compile them into a valid encrypted .rpa archive.
"""

from pathlib import Path
from typing import Optional
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton, QTextEdit, QVBoxLayout, QWidget
from core.logger import logger
from core.rpa_repacker import RpaArchiveWriter


class RepackWorkerThread(QThread):
    """Background worker thread for repacking RPA archives."""

    progress = Signal(int, int, str)
    finished = Signal(bool, str)

    def __init__(self, source_dir: str, output_path: str, format_version: str, key_hex: str) -> None:
        super().__init__()
        self.source_dir = source_dir
        self.output_path = output_path
        self.format_version = format_version
        self.key_hex = key_hex

    def run(self) -> None:
        try:
            key_val = int(self.key_hex, 16) if self.key_hex.strip() else 0x0424b2b4
            writer = RpaArchiveWriter(self.output_path, format_version=self.format_version, key=key_val)
            file_map = writer.add_directory(self.source_dir)

            def callback(curr, tot, fname):
                self.progress.emit(curr, tot, fname)

            writer.pack(file_map, progress_callback=callback)
            self.finished.emit(True, f"Successfully created archive: {self.output_path}")
        except Exception as e:
            logger.error(f"Repack worker error: {e}")
            self.finished.emit(False, str(e))


class RepackerTabWidget(QWidget):
    """GUI Tab for compiling directory into .rpa archives."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.worker: Optional[RepackWorkerThread] = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Title & Description
        title = QLabel("RPA Archive Compiler (Repacker)")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6;")
        desc = QLabel("Package customized assets into an encrypted/obfuscated Ren'Py Archive (.rpa) file.")
        desc.setStyleSheet("color: #94a3b8;")

        layout.addWidget(title)
        layout.addWidget(desc)

        # Settings Card
        card = QFrame()
        card.setObjectName("Card")
        form = QFormLayout(card)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)

        # Source Dir
        self.src_entry = QLineEdit()
        self.src_entry.setPlaceholderText("Select folder containing files to pack...")
        src_btn = QPushButton("Browse Source")
        src_btn.setObjectName("SecondaryBtn")
        src_btn.clicked.connect(self._browse_src)

        src_box = QHBoxLayout()
        src_box.addWidget(self.src_entry)
        src_box.addWidget(src_btn)
        form.addRow("Source Directory:", src_box)

        # Output File
        self.out_entry = QLineEdit()
        self.out_entry.setPlaceholderText("Select output .rpa file path...")
        out_btn = QPushButton("Browse Output")
        out_btn.setObjectName("SecondaryBtn")
        out_btn.clicked.connect(self._browse_out)

        out_box = QHBoxLayout()
        out_box.addWidget(self.out_entry)
        out_box.addWidget(out_btn)
        form.addRow("Target Archive (.rpa):", out_box)

        # Format Version
        self.ver_combo = QComboBox()
        self.ver_combo.addItems(["RPA-3.0", "RPA-2.0"])
        form.addRow("Archive Version:", self.ver_combo)

        # XOR Key
        self.key_entry = QLineEdit("0424b2b4")
        self.key_entry.setPlaceholderText("e.g. 0424b2b4 (Hexadecimal 32-bit key)")
        form.addRow("Custom XOR Key (Hex):", self.key_entry)

        layout.addWidget(card)

        # Pack Action Button
        self.pack_btn = QPushButton("Pack Archive (.rpa)")
        self.pack_btn.setMinimumHeight(38)
        self.pack_btn.clicked.connect(self._start_pack)
        layout.addWidget(self.pack_btn)

        # Progress & Log Output
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("Repacking status and build output log...")
        layout.addWidget(self.log_box, 1)

    def _browse_src(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select Folder to Pack into RPA")
        if d:
            self.src_entry.setText(d)
            if not self.out_entry.text():
                p = Path(d)
                self.out_entry.setText(str(p.parent / f"{p.name}.rpa"))

    def _browse_out(self) -> None:
        f, _ = QFileDialog.getSaveFileName(self, "Save RPA Archive As", "", "Ren'Py Archive (*.rpa)")
        if f:
            self.out_entry.setText(f)

    def _start_pack(self) -> None:
        src = self.src_entry.text().strip()
        out = self.out_entry.text().strip()

        if not src or not Path(src).is_dir():
            self.log_box.append("Error: Please select a valid source directory.")
            return
        if not out:
            self.log_box.append("Error: Please select a target .rpa output file path.")
            return

        self.pack_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_box.clear()
        self.log_box.append(f"Starting repacking of folder: {src} -> {out}")

        ver = self.ver_combo.currentText()
        key_str = self.key_entry.text()

        self.worker = RepackWorkerThread(src, out, ver, key_str)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, current: int, total: int, filename: str) -> None:
        pct = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.log_box.append(f"[{current}/{total}] Packed: {filename}")

    def _on_finished(self, success: bool, msg: str) -> None:
        self.pack_btn.setEnabled(True)
        if success:
            self.progress_bar.setValue(100)
            self.log_box.append(f"\nSUCCESS: {msg}")
        else:
            self.log_box.append(f"\nFAILED: {msg}")
