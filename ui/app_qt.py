"""Main PySide6 Application Window for Ren'Py Asset Extraction Tool v2.0.

Provides modern Qt6 responsive layout with resizable splitters, asset tree navigation,
interactive media previews, repacker, decompiler, and smart search HUD.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.archive_reader import RpaArchiveReader
from core.config import CATEGORY_FOLDERS, SUPPORTED_EXTENSIONS
from core.logger import logger
from core.metadata import MetadataManager
from core.scanner import AssetScanner
from core.settings import BaseSettings
from core.smart_filter import SmartFilterEngine
from parsers.script_parser import ScriptParser
from ui.syntax_highlighter import RenPySyntaxHighlighter
from ui.theme import apply_theme
from ui.widgets.audio_player import InteractiveAudioPlayer
from ui.widgets.decompiler_tab import DecompilerTabWidget
from ui.widgets.filter_hud import FilterHudBar
from ui.widgets.image_inspector import ImageInspector
from ui.widgets.repacker_tab import RepackerTabWidget
from ui.widgets.v3_studio_tab import V3StudioTabWidget
from ui.widgets.video_player import InteractiveVideoPlayer


class QtLogSinkSignal(QThread):
    """Bridge for emitting log messages safely to the Qt GUI log text box."""
    messageLogged = Signal(str)


class QtScanWorkerThread(QThread):
    """Background worker for scanning target game directory or archive."""
    scanCompleted = Signal(object)
    scanFailed = Signal(str)

    def __init__(self, target_path: Path) -> None:
        super().__init__()
        self.target_path = target_path

    def run(self) -> None:
        try:
            scanner = AssetScanner(self.target_path)
            scanner.scan()
            self.scanCompleted.emit(scanner)
        except Exception as e:
            logger.error(f"Scan worker failed: {e}")
            self.scanFailed.emit(str(e))


class QtExtractWorkerThread(QThread):
    """Background worker for extracting assets."""
    progress = Signal(int, int, str)
    extractionFinished = Signal(int, float)

    def __init__(self, scanner: AssetScanner, output_dir: Path, categories: List[str], overwrite: str, fast_mode: bool) -> None:
        super().__init__()
        self.scanner = scanner
        self.output_dir = output_dir
        self.categories = categories
        self.overwrite = overwrite
        self.fast_mode = fast_mode

    def run(self) -> None:
        import time
        start_time = time.time()
        output_path = Path(self.output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
        meta_mgr = MetadataManager(output_path)
        total_extracted = 0

        # Gather files
        archive_tasks = []
        for rpa in self.scanner.archives:
            try:
                reader = RpaArchiveReader(rpa)
                files = reader.get_filtered_files(self.categories)
                for f in files:
                    archive_tasks.append((reader, f))
            except Exception as e:
                logger.error(f"Failed to read index for {rpa}: {e}")

        total_files = len(archive_tasks)
        for idx, (reader, fname) in enumerate(archive_tasks, 1):
            try:
                extracted = reader.extract_file(fname, output_path, self.overwrite)
                meta_mgr.register_file(rel_path=fname, original_source=reader.archive_path.name, file_path=extracted, fast_mode=self.fast_mode)
                total_extracted += 1
                self.progress.emit(idx, total_files, fname)
            except Exception as e:
                logger.error(f"Error extracting {fname}: {e}")

        meta_mgr.save()
        elapsed = time.time() - start_time
        self.extractionFinished.emit(total_extracted, elapsed)


class RenPyExtractorQtApp(QMainWindow):
    """Main window interface for Ren'Py Asset Extraction Tool v2.0."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Ren'Py Asset Extraction Tool v2.0")
        self.resize(1240, 820)
        self.setMinimumSize(1020, 680)

        self.scanner: Optional[AssetScanner] = None
        self.all_scanned_assets: List[Dict[str, Any]] = []
        self.scanned_readers: Dict[str, RpaArchiveReader] = {}

        self._init_ui()
        self._connect_logger()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Top Filter HUD Bar
        self.filter_hud = FilterHudBar()
        self.filter_hud.filterChanged.connect(self._apply_asset_filter)
        main_layout.addWidget(self.filter_hud)

        # Center Main Splitter (Sidebar + Tabs)
        self.main_splitter = QSplitter(Qt.Horizontal)

        # 1. Left Sidebar Panel
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setMaximumWidth(310)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(10)

        side_title = QLabel("Control Panel")
        side_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        sidebar_layout.addWidget(side_title)

        # Input Browse
        sidebar_layout.addWidget(QLabel("Game Directory / Archive:"))
        self.input_entry = QLineEdit()
        self.input_entry.setPlaceholderText("No target selected...")
        input_btn = QPushButton("Browse Target")
        input_btn.setObjectName("SecondaryBtn")
        input_btn.clicked.connect(self._browse_input)
        in_box = QHBoxLayout()
        in_box.addWidget(self.input_entry)
        in_box.addWidget(input_btn)
        sidebar_layout.addLayout(in_box)

        # Output Browse
        sidebar_layout.addWidget(QLabel("Output Directory:"))
        self.output_entry = QLineEdit(BaseSettings.output_dir or "")
        self.output_entry.setPlaceholderText("No output directory...")
        output_btn = QPushButton("Browse Output")
        output_btn.setObjectName("SecondaryBtn")
        output_btn.clicked.connect(self._browse_output)
        out_box = QHBoxLayout()
        out_box.addWidget(self.output_entry)
        out_box.addWidget(output_btn)
        sidebar_layout.addLayout(out_box)

        # Category Checkboxes
        cat_group = QGroupBox("Selective Categories")
        cat_layout = QVBoxLayout(cat_group)
        self.cat_checkboxes: Dict[str, QCheckBox] = {}
        for cat in SUPPORTED_EXTENSIONS.keys():
            chk = QCheckBox(cat.capitalize())
            chk.setChecked(cat in BaseSettings.selected_categories)
            self.cat_checkboxes[cat] = chk
            cat_layout.addWidget(chk)
        sidebar_layout.addWidget(cat_group)

        # Overwrite Dropdown
        sidebar_layout.addWidget(QLabel("Overwrite Mode:"))
        self.overwrite_combo = QComboBox()
        self.overwrite_combo.addItems(["skip", "overwrite", "rename"])
        self.overwrite_combo.setCurrentText(BaseSettings.overwrite_mode)
        sidebar_layout.addWidget(self.overwrite_combo)

        # Fast Mode Checkbox
        self.fast_chk = QCheckBox("Fast Mode (Skip Metadata)")
        self.fast_chk.setChecked(BaseSettings.fast_mode)
        sidebar_layout.addWidget(self.fast_chk)

        # Action Buttons
        self.scan_btn = QPushButton("Scan Game Folder")
        self.scan_btn.clicked.connect(self._start_scan)
        sidebar_layout.addWidget(self.scan_btn)

        self.extract_btn = QPushButton("Unpack Selected Assets")
        self.extract_btn.setStyleSheet("background-color: #059669;")
        self.extract_btn.clicked.connect(self._start_extraction)
        sidebar_layout.addWidget(self.extract_btn)

        sidebar_layout.addStretch()
        self.main_splitter.addWidget(self.sidebar)

        # 2. Right Workspace Tabbed Panel
        self.tab_widget = QTabWidget()

        # Tab 1: Asset Explorer (Tree + Media Preview Splitter)
        explorer_widget = QWidget()
        explorer_layout = QVBoxLayout(explorer_widget)
        explorer_layout.setContentsMargins(4, 4, 4, 4)

        self.explorer_splitter = QSplitter(Qt.Horizontal)

        # Tree View of Assets
        self.asset_tree = QTreeWidget()
        self.asset_tree.setHeaderLabels(["Asset Name / Path", "Category", "Size", "Info"])
        self.asset_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.asset_tree.itemClicked.connect(self._on_tree_item_clicked)
        self.explorer_splitter.addWidget(self.asset_tree)

        # Right Preview Switcher Widget
        self.preview_panel = QTabWidget()

        # Preview Cards
        self.img_inspector = ImageInspector()
        self.audio_player = InteractiveAudioPlayer()
        self.video_player = InteractiveVideoPlayer()

        self.text_preview = QPlainTextEdit()
        self.text_preview.setFont(QFont("Consolas", 10))
        self.script_highlighter = RenPySyntaxHighlighter(self.text_preview.document())

        self.info_preview = QTextEdit()
        self.info_preview.setReadOnly(True)

        self.preview_panel.addTab(self.img_inspector, "Image Inspector")
        self.preview_panel.addTab(self.audio_player, "Audio Player")
        self.preview_panel.addTab(self.video_player, "Video Player")
        self.preview_panel.addTab(self.text_preview, "Script Viewer")
        self.preview_panel.addTab(self.info_preview, "Metadata")

        self.explorer_splitter.addWidget(self.preview_panel)
        self.explorer_splitter.setSizes([450, 550])

        explorer_layout.addWidget(self.explorer_splitter)
        self.tab_widget.addTab(explorer_widget, "Asset Explorer")

        # Tab 2: RPA Repacker
        self.repacker_tab = RepackerTabWidget()
        self.tab_widget.addTab(self.repacker_tab, "RPA Repacker")

        # Tab 3: .rpyc Decompiler
        self.decompiler_tab = DecompilerTabWidget()
        self.tab_widget.addTab(self.decompiler_tab, ".rpyc Decompiler")

        # Tab 4: v3.0 Studio
        self.v3_studio_tab = V3StudioTabWidget()
        self.tab_widget.addTab(self.v3_studio_tab, "v3.0 Studio")

        self.main_splitter.addWidget(self.tab_widget)
        self.main_splitter.setSizes([280, 960])

        main_layout.addWidget(self.main_splitter, 1)

        # Bottom Log Box & Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.log_box = QTextEdit()
        self.log_box.setMaximumHeight(120)
        self.log_box.setReadOnly(True)
        main_layout.addWidget(self.log_box)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _connect_logger(self) -> None:
        self.log_bridge = QtLogSinkSignal()
        self.log_bridge.messageLogged.connect(self._append_log_message)

        class QtLogHandler:
            def __init__(self, bridge: QtLogSinkSignal):
                self.bridge = bridge

            def write(self, msg: str):
                if msg.strip():
                    self.bridge.messageLogged.emit(msg.strip())

            def flush(self):
                pass

        logger.add(QtLogHandler(self.log_bridge), format="{message}", level="INFO")

    def _append_log_message(self, msg: str) -> None:
        self.log_box.append(msg)

    def _browse_input(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select Game Directory")
        if d:
            self.input_entry.setText(d)

    def _browse_output(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if d:
            self.output_entry.setText(d)

    def _start_scan(self) -> None:
        target = self.input_entry.text().strip()
        if not target or not Path(target).exists():
            logger.error("Invalid input target directory.")
            return

        self.scan_btn.setEnabled(False)
        self.status_bar.showMessage("Scanning game directory...")

        self.scan_thread = QtScanWorkerThread(Path(target))
        self.scan_thread.scanCompleted.connect(self._on_scan_completed)
        self.scan_thread.scanFailed.connect(self._on_scan_failed)
        self.scan_thread.start()

    def _on_scan_completed(self, scanner: AssetScanner) -> None:
        self.scan_btn.setEnabled(True)
        self.scanner = scanner
        self.status_bar.showMessage("Scan complete.")
        self.asset_tree.clear()
        self.all_scanned_assets.clear()
        self.scanned_readers.clear()

        # Build Archives tree nodes
        rpa_root = QTreeWidgetItem(self.asset_tree, ["RPA Archives", "", "", f"{len(scanner.archives)} archives"])
        for rpa in scanner.archives:
            r_item = QTreeWidgetItem(rpa_root, [rpa.name, "archive", "", ""])
            try:
                reader = RpaArchiveReader(rpa)
                self.scanned_readers[rpa.name] = reader
                idx = reader.read_index()
                for fname, entries in idx.items():
                    size = sum(e[1] for e in entries)
                    c_item = QTreeWidgetItem(r_item, [fname, "archive_entry", self._format_size(size), ""])
                    c_item.setData(0, Qt.UserRole, {"type": "rpa_entry", "rpa_name": rpa.name, "fname": fname, "size": size})

                    cat = "data"
                    ext = Path(fname).suffix.lower()
                    for k, exts in SUPPORTED_EXTENSIONS.items():
                        if ext in exts:
                            cat = k
                            break

                    self.all_scanned_assets.append({
                        "name": Path(fname).name,
                        "rel_path": fname,
                        "category": cat,
                        "size_bytes": size,
                        "rpa_name": rpa.name,
                        "tree_item": c_item,
                    })
            except Exception as e:
                logger.error(f"Error indexing {rpa.name}: {e}")

        # Build Standalone assets nodes
        loose_root = QTreeWidgetItem(self.asset_tree, ["Standalone Assets", "", "", ""])
        for cat, assets in scanner.standalone_assets.items():
            if assets:
                cat_node = QTreeWidgetItem(loose_root, [cat.capitalize(), "", "", f"{len(assets)} files"])
                for a in assets:
                    sz = a.stat().st_size if a.exists() else 0
                    a_item = QTreeWidgetItem(cat_node, [a.name, cat, self._format_size(sz), ""])
                    a_item.setData(0, Qt.UserRole, {"type": "standalone", "path": str(a)})
                    self.all_scanned_assets.append({
                        "name": a.name,
                        "rel_path": a.name,
                        "category": cat,
                        "size_bytes": sz,
                        "path": str(a),
                        "tree_item": a_item,
                    })

        self.asset_tree.expandAll()
        logger.info(f"Loaded asset tree with {len(self.all_scanned_assets)} assets.")

    def _on_scan_failed(self, err: str) -> None:
        self.scan_btn.setEnabled(True)
        self.status_bar.showMessage(f"Scan failed: {err}")

    def _apply_asset_filter(self, query_text: str) -> None:
        if not self.all_scanned_assets:
            return
        filtered = SmartFilterEngine.filter_assets(self.all_scanned_assets, query_text)
        filtered_items = set(a["tree_item"] for a in filtered)

        for asset in self.all_scanned_assets:
            item = asset["tree_item"]
            item.setHidden(item not in filtered_items)

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, col: int) -> None:
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        item_type = data.get("type")
        if item_type == "rpa_entry":
            rpa_name = data["rpa_name"]
            fname = data["fname"]
            reader = self.scanned_readers.get(rpa_name)
            if reader:
                try:
                    file_bytes = reader.read_file_bytes(fname)
                    self._preview_bytes(fname, file_bytes)
                except Exception as e:
                    logger.error(f"Failed to read file bytes: {e}")
        elif item_type == "standalone":
            file_path = Path(data["path"])
            if file_path.exists():
                ext = file_path.suffix.lower()
                if ext in SUPPORTED_EXTENSIONS["images"]:
                    self.img_inspector.load_image(file_path)
                    self.preview_panel.setCurrentWidget(self.img_inspector)
                elif ext in SUPPORTED_EXTENSIONS["audio"]:
                    self.audio_player.load_audio(file_path)
                    self.preview_panel.setCurrentWidget(self.audio_player)
                elif ext in SUPPORTED_EXTENSIONS["video"]:
                    self.video_player.load_video(file_path)
                    self.preview_panel.setCurrentWidget(self.video_player)
                elif ext in SUPPORTED_EXTENSIONS["scripts"]:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        self.text_preview.setPlainText(f.read())
                    self.preview_panel.setCurrentWidget(self.text_preview)

    def _preview_bytes(self, fname: str, data: bytes) -> None:
        ext = Path(fname).suffix.lower()
        if ext in SUPPORTED_EXTENSIONS["images"]:
            self.img_inspector.load_image(data)
            self.preview_panel.setCurrentWidget(self.img_inspector)
        elif ext in SUPPORTED_EXTENSIONS["scripts"]:
            self.text_preview.setPlainText(data.decode("utf-8", errors="ignore"))
            self.preview_panel.setCurrentWidget(self.text_preview)

    def _start_extraction(self) -> None:
        if not self.scanner:
            logger.error("Please run scan first.")
            return

        out = self.output_entry.text().strip()
        if not out:
            logger.error("Please select an output directory.")
            return

        active_cats = [c for c, chk in self.cat_checkboxes.items() if chk.isChecked()]
        ow = self.overwrite_combo.currentText()
        fast = self.fast_chk.isChecked()

        self.extract_btn.setEnabled(False)
        self.progress_bar.setVisible(True)

        self.extract_thread = QtExtractWorkerThread(self.scanner, Path(out), active_cats, ow, fast)
        self.extract_thread.progress.connect(self._on_extract_progress)
        self.extract_thread.extractionFinished.connect(self._on_extract_finished)
        self.extract_thread.start()

    def _on_extract_progress(self, current: int, total: int, fname: str) -> None:
        pct = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)

    def _on_extract_finished(self, total: int, elapsed: float) -> None:
        self.extract_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        logger.info(f"Extraction complete! Extracted {total} files in {elapsed:.2f} seconds.")

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes} B"


def main_qt() -> None:
    app = QApplication(sys.argv)
    apply_theme(app, dark_mode=True)
    window = RenPyExtractorQtApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main_qt()
