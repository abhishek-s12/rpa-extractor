"""Built-in .rpyc Decompiler GUI Tab.

Reverse compiles Ren'Py compiled script files (.rpyc) back into editable .rpy scripts
with syntax highlighting and file export capabilities.
"""

from pathlib import Path
from typing import List
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton, QSplitter, QVBoxLayout, QWidget
from core.logger import logger
from parsers.rpyc_decompiler import RpycDecompiler
from ui.syntax_highlighter import RenPySyntaxHighlighter


class DecompilerTabWidget(QWidget):
    """GUI Tab for decompiling .rpyc files into editable .rpy scripts."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.selected_files: List[Path] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Title
        title = QLabel("Built-in .rpyc Script Decompiler")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6;")
        desc = QLabel("Decompile compiled Ren'Py script files (.rpyc / .rpymc) into human-readable .rpy files.")
        desc.setStyleSheet("color: #94a3b8;")

        layout.addWidget(title)
        layout.addWidget(desc)

        # Main Splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left Panel: File Selection & List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        btn_row = QHBoxLayout()
        self.add_files_btn = QPushButton("Add .rpyc Files")
        self.add_files_btn.clicked.connect(self._add_files)

        self.add_dir_btn = QPushButton("Add Folder")
        self.add_dir_btn.setObjectName("SecondaryBtn")
        self.add_dir_btn.clicked.connect(self._add_dir)

        btn_row.addWidget(self.add_files_btn)
        btn_row.addWidget(self.add_dir_btn)
        left_layout.addLayout(btn_row)

        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self._on_item_clicked)
        left_layout.addWidget(self.file_list, 1)

        self.decompile_all_btn = QPushButton("Decompile All Files")
        self.decompile_all_btn.clicked.connect(self._decompile_all)
        left_layout.addWidget(self.decompile_all_btn)

        splitter.addWidget(left_widget)

        # Right Panel: Decompiled Code View with Syntax Highlighting
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_header = QHBoxLayout()
        self.preview_label = QLabel("Script Preview (Select a file)")
        self.preview_label.setFont(QFont("Segoe UI", 10, QFont.Bold))

        self.save_rpy_btn = QPushButton("Save Decompiled .rpy")
        self.save_rpy_btn.setObjectName("SecondaryBtn")
        self.save_rpy_btn.clicked.connect(self._save_current_rpy)

        right_header.addWidget(self.preview_label)
        right_header.addStretch()
        right_header.addWidget(self.save_rpy_btn)
        right_layout.addLayout(right_header)

        self.code_edit = QPlainTextEdit()
        self.code_edit.setFont(QFont("Consolas", 10))
        self.code_edit.setReadOnly(False)
        self.highlighter = RenPySyntaxHighlighter(self.code_edit.document())

        right_layout.addWidget(self.code_edit, 1)
        splitter.addWidget(right_widget)

        splitter.setSizes([300, 700])
        layout.addWidget(splitter, 1)


    def _add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Select .rpyc Files", "", "Ren'Py Compiled Script (*.rpyc *.rpymc)")
        for f in files:
            p = Path(f)
            if p not in self.selected_files:
                self.selected_files.append(p)
                self.file_list.addItem(p.name)

    def _add_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select Folder Containing .rpyc Files")
        if d:
            p_dir = Path(d)
            for p in p_dir.rglob("*.rpyc"):
                if p not in self.selected_files:
                    self.selected_files.append(p)
                    self.file_list.addItem(p.name)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        idx = self.file_list.row(item)
        if 0 <= idx < len(self.selected_files):
            file_path = self.selected_files[idx]
            self.preview_label.setText(f"Script Preview: {file_path.name}")
            decompiled_text = RpycDecompiler.decompile(file_path)
            self.code_edit.setPlainText(decompiled_text)

    def _save_current_rpy(self) -> None:
        curr_row = self.file_list.currentRow()
        if curr_row >= 0 and curr_row < len(self.selected_files):
            src_p = self.selected_files[curr_row]
            default_out = str(src_p.with_suffix(".rpy"))
            f, _ = QFileDialog.getSaveFileName(self, "Save Decompiled Script", default_out, "Ren'Py Script (*.rpy)")
            if f:
                with open(f, "w", encoding="utf-8") as out_file:
                    out_file.write(self.code_edit.toPlainText())
                logger.info(f"Saved decompiled script to {f}")

    def _decompile_all(self) -> None:
        if not self.selected_files:
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Select Destination Directory for Decompiled .rpy Files")
        if not out_dir:
            return

        out_path = Path(out_dir)
        count = 0
        for p in self.selected_files:
            try:
                dest = out_path / f"{p.stem}.rpy"
                text = RpycDecompiler.decompile(p)
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(text)
                count += 1
            except Exception as e:
                logger.error(f"Failed to decompile {p}: {e}")

        logger.info(f"Successfully decompiled {count}/{len(self.selected_files)} files to {out_dir}")
