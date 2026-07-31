"""V3 Studio Tab Widget for PySide6 Desktop GUI.

Provides graphical interfaces for script translation, AI image tagging, live memory patching,
hot-reloading, version diffing, 4K upscaling, media transcoding, and community plugins.
"""

from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.logger import logger
from core.plugin_sdk import PluginRegistry


class V3StudioTabWidget(QWidget):
    """Integrated v3.0 Studio Tab containing AI, Live Interception, Media Pipeline & Plugins UI."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        title_label = QLabel("⚡ Ren'Py Extraction Tool v3.0 - Studio & AI Suite")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #7b68ee; margin-bottom: 10px;")
        main_layout.addWidget(title_label)

        self.sub_tabs = QTabWidget()
        main_layout.addWidget(self.sub_tabs)

        # 1. AI Translation & Tagging Tab
        self.sub_tabs.addTab(self._create_ai_tab(), "🤖 AI & Localization")

        # 2. Live Interception & Hot Reload Tab
        self.sub_tabs.addTab(self._create_live_tab(), "⚡ Live Interception")

        # 3. Version Visual & Audio Diffing Tab
        self.sub_tabs.addTab(self._create_diff_tab(), "🔍 Version Diffing")

        # 4. Media Processing & Plugins Tab
        self.sub_tabs.addTab(self._create_media_tab(), "🎨 Media & Plugins")

    def _create_ai_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Script Translation Group
        trans_group = QGroupBox("Automated Script Translation Engine")
        trans_layout = QFormLayout(trans_group)

        self.script_path_edit = QLineEdit()
        btn_browse_script = QPushButton("Browse...")
        btn_browse_script.clicked.connect(self._browse_script)

        script_h_layout = QHBoxLayout()
        script_h_layout.addWidget(self.script_path_edit)
        script_h_layout.addWidget(btn_browse_script)
        trans_layout.addRow("Script (.rpy) or Directory:", script_h_layout)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Spanish", "French", "German", "Japanese", "Chinese", "Russian"])
        trans_layout.addRow("Target Language:", self.lang_combo)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("Optional: Gemini API Key (Uses offline mode if blank)")
        trans_layout.addRow("Gemini API Key:", self.api_key_edit)

        btn_run_translate = QPushButton("🚀 Run Script Translation")
        btn_run_translate.setStyleSheet("background-color: #6c5ce7; font-weight: bold;")
        btn_run_translate.clicked.connect(self._run_translation)
        trans_layout.addRow(btn_run_translate)

        layout.addWidget(trans_group)

        # Intelligent Image Tagging Group
        tag_group = QGroupBox("Intelligent Image & Scene Tagging")
        tag_layout = QFormLayout(tag_group)

        self.tag_dir_edit = QLineEdit()
        btn_browse_tag = QPushButton("Browse...")
        btn_browse_tag.clicked.connect(self._browse_tag_dir)

        tag_h_layout = QHBoxLayout()
        tag_h_layout.addWidget(self.tag_dir_edit)
        tag_h_layout.addWidget(btn_browse_tag)
        tag_layout.addRow("Extracted Assets Directory:", tag_h_layout)

        btn_run_tagging = QPushButton("🏷️ Index Assets with AI Tags")
        btn_run_tagging.setStyleSheet("background-color: #2e8b57; font-weight: bold;")
        btn_run_tagging.clicked.connect(self._run_tagging)
        tag_layout.addRow(btn_run_tagging)

        layout.addWidget(tag_group)
        layout.addStretch()
        return widget

    def _create_live_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Live RPA Override Group
        override_group = QGroupBox("In-Memory RPA Override Process Hooker")
        override_layout = QFormLayout(override_group)

        self.game_dir_edit = QLineEdit()
        btn_browse_game = QPushButton("Browse...")
        btn_browse_game.clicked.connect(lambda: self._browse_dir(self.game_dir_edit))

        game_h = QHBoxLayout()
        game_h.addWidget(self.game_dir_edit)
        game_h.addWidget(btn_browse_game)
        override_layout.addRow("Target Ren'Py Game Path:", game_h)

        self.mod_dir_edit = QLineEdit()
        btn_browse_mod = QPushButton("Browse...")
        btn_browse_mod.clicked.connect(lambda: self._browse_dir(self.mod_dir_edit))

        mod_h = QHBoxLayout()
        mod_h.addWidget(self.mod_dir_edit)
        mod_h.addWidget(btn_browse_mod)
        override_layout.addRow("Modded Assets Directory:", mod_h)

        btn_inject = QPushButton("💉 Inject Live Memory RPA Hook")
        btn_inject.clicked.connect(self._inject_hook)
        btn_remove = QPushButton("❌ Remove Live Hook")
        btn_remove.clicked.connect(self._remove_hook)

        btn_h = QHBoxLayout()
        btn_h.addWidget(btn_inject)
        btn_h.addWidget(btn_remove)
        override_layout.addRow(btn_h)

        layout.addWidget(override_group)

        # Hot Reloading Studio Group
        hot_group = QGroupBox("Hot-Reloading Studio (Asset Directory Watcher)")
        hot_layout = QFormLayout(hot_group)

        self.hot_dir_edit = QLineEdit()
        btn_browse_hot = QPushButton("Browse...")
        btn_browse_hot.clicked.connect(lambda: self._browse_dir(self.hot_dir_edit))

        hot_h = QHBoxLayout()
        hot_h.addWidget(self.hot_dir_edit)
        hot_h.addWidget(btn_browse_hot)
        hot_layout.addRow("Watch Asset Directory:", hot_h)

        self.btn_toggle_watch = QPushButton("▶ Start Hot-Reloading Watcher")
        self.btn_toggle_watch.clicked.connect(self._toggle_watcher)
        hot_layout.addRow(self.btn_toggle_watch)

        layout.addWidget(hot_group)
        layout.addStretch()

        self.hot_studio = None
        return widget

    def _create_diff_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        diff_group = QGroupBox("Asset Version Comparator & Visual/Audio Diffing")
        diff_layout = QFormLayout(diff_group)

        self.v1_dir_edit = QLineEdit()
        btn_v1 = QPushButton("Browse...")
        btn_v1.clicked.connect(lambda: self._browse_dir(self.v1_dir_edit))
        h1 = QHBoxLayout()
        h1.addWidget(self.v1_dir_edit)
        h1.addWidget(btn_v1)
        diff_layout.addRow("Version 1 (Original) Folder:", h1)

        self.v2_dir_edit = QLineEdit()
        btn_v2 = QPushButton("Browse...")
        btn_v2.clicked.connect(lambda: self._browse_dir(self.v2_dir_edit))
        h2 = QHBoxLayout()
        h2.addWidget(self.v2_dir_edit)
        h2.addWidget(btn_v2)
        diff_layout.addRow("Version 2 (Updated) Folder:", h2)

        self.diff_out_edit = QLineEdit()
        btn_diff_out = QPushButton("Browse...")
        btn_diff_out.clicked.connect(lambda: self._browse_dir(self.diff_out_edit))
        ho = QHBoxLayout()
        ho.addWidget(self.diff_out_edit)
        ho.addWidget(btn_diff_out)
        diff_layout.addRow("Diff Output Folder:", ho)

        btn_run_diff = QPushButton("📊 Compare Versions & Generate Heatmaps")
        btn_run_diff.setStyleSheet("background-color: #d63031; font-weight: bold;")
        btn_run_diff.clicked.connect(self._run_version_diff)
        diff_layout.addRow(btn_run_diff)

        layout.addWidget(diff_group)

        self.diff_log_text = QTextEdit()
        self.diff_log_text.setReadOnly(True)
        layout.addWidget(self.diff_log_text)
        return widget

    def _create_media_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Upscaler & Transparency
        up_group = QGroupBox("Integrated 4K Texture Upscaler & Sprite Cleaning")
        up_layout = QFormLayout(up_group)

        self.up_file_edit = QLineEdit()
        btn_browse_up = QPushButton("Browse...")
        btn_browse_up.clicked.connect(lambda: self._browse_file(self.up_file_edit))
        h_up = QHBoxLayout()
        h_up.addWidget(self.up_file_edit)
        h_up.addWidget(btn_browse_up)
        up_layout.addRow("Input Image Path:", h_up)

        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(2, 4)
        self.scale_spin.setValue(2)
        up_layout.addRow("Upscale Scale Factor:", self.scale_spin)

        btn_upscale = QPushButton("✨ Upscale Image")
        btn_upscale.clicked.connect(self._run_upscale)
        btn_clean_alpha = QPushButton("🧹 Clean Alpha Border Halos")
        btn_clean_alpha.clicked.connect(self._run_clean_alpha)

        h_btns = QHBoxLayout()
        h_btns.addWidget(btn_upscale)
        h_btns.addWidget(btn_clean_alpha)
        up_layout.addRow(h_btns)

        layout.addWidget(up_group)

        # Plugin SDK
        plugin_group = QGroupBox("Community Extractor Plugin SDK")
        plugin_layout = QVBoxLayout(plugin_group)

        self.plugin_list_widget = QListWidget()
        plugin_layout.addWidget(self.plugin_list_widget)

        btn_refresh_plugins = QPushButton("🔄 Refresh Plugins")
        btn_refresh_plugins.clicked.connect(self._refresh_plugins)
        plugin_layout.addWidget(btn_refresh_plugins)

        layout.addWidget(plugin_group)
        self._refresh_plugins()

        return widget

    # Helper callbacks
    def _browse_script(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Ren'Py Script", "", "Ren'Py Script (*.rpy)")
        if path:
            self.script_path_edit.setText(path)

    def _browse_tag_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.tag_dir_edit.setText(path)

    def _browse_dir(self, line_edit: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            line_edit.setText(path)

    def _browse_file(self, line_edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Image File", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            line_edit.setText(path)

    def _run_translation(self) -> None:
        path_str = self.script_path_edit.text().strip()
        if not path_str:
            QMessageBox.warning(self, "Warning", "Please select a script file or directory.")
            return

        from parsers.translation_engine import RenpyScriptTranslator
        translator = RenpyScriptTranslator(
            api_key=self.api_key_edit.text().strip() or None,
            target_lang=self.lang_combo.currentText(),
        )

        p = Path(path_str)
        try:
            if p.is_file():
                out = translator.translate_script_file(p)
                QMessageBox.information(self, "Success", f"Translated script saved to:\n{out}")
            elif p.is_dir():
                out_dir = p.parent / f"{p.name}_{self.lang_combo.currentText().lower()}"
                res = translator.translate_directory(p, out_dir)
                QMessageBox.information(self, "Success", f"Successfully translated {len(res)} scripts into:\n{out_dir}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Translation failed: {e}")

    def _run_tagging(self) -> None:
        dir_str = self.tag_dir_edit.text().strip()
        if not dir_str:
            QMessageBox.warning(self, "Warning", "Please select an extracted assets directory.")
            return

        from extractors.image_tagger import SmartMetadataIndexer
        try:
            catalog = SmartMetadataIndexer.index_directory(Path(dir_str))
            QMessageBox.information(self, "Success", f"Successfully indexed {len(catalog)} assets with AI tags.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Tagging failed: {e}")

    def _inject_hook(self) -> None:
        game_str = self.game_dir_edit.text().strip()
        mod_str = self.mod_dir_edit.text().strip()
        if not game_str or not mod_str:
            QMessageBox.warning(self, "Warning", "Please select both target game path and modded assets directory.")
            return

        from core.live_interceptor import RenPyProcessHooker
        try:
            hook_file = RenPyProcessHooker.inject_rpa_override_hook(Path(game_str), Path(mod_str))
            QMessageBox.information(self, "Success", f"Live In-Memory RPA Override Hook injected into:\n{hook_file}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Hook injection failed: {e}")

    def _remove_hook(self) -> None:
        game_str = self.game_dir_edit.text().strip()
        if not game_str:
            QMessageBox.warning(self, "Warning", "Please select target game path.")
            return

        from core.live_interceptor import RenPyProcessHooker
        if RenPyProcessHooker.remove_override_hook(Path(game_str)):
            QMessageBox.information(self, "Success", "Live RPA Override Hook removed successfully.")
        else:
            QMessageBox.information(self, "Info", "No injected override hook found.")

    def _toggle_watcher(self) -> None:
        if self.hot_studio and self.hot_studio.observer and self.hot_studio.observer.is_alive():
            self.hot_studio.stop()
            self.hot_studio = None
            self.btn_toggle_watch.setText("▶ Start Hot-Reloading Watcher")
            self.btn_toggle_watch.setStyleSheet("")
            QMessageBox.information(self, "Info", "Hot-Reloading Watcher stopped.")
        else:
            watch_str = self.hot_dir_edit.text().strip()
            if not watch_str:
                QMessageBox.warning(self, "Warning", "Please select an asset directory to watch.")
                return

            from core.live_interceptor import HotReloadStudio
            self.hot_studio = HotReloadStudio(Path(watch_str))
            self.hot_studio.start()
            self.btn_toggle_watch.setText("⏹ Stop Hot-Reloading Watcher")
            self.btn_toggle_watch.setStyleSheet("background-color: #e74c3c; color: #fff; font-weight: bold;")
            QMessageBox.information(self, "Success", f"Hot-Reloading Watcher actively monitoring:\n{watch_str}")

    def _run_version_diff(self) -> None:
        v1_str = self.v1_dir_edit.text().strip()
        v2_str = self.v2_dir_edit.text().strip()
        diff_out_str = self.diff_out_edit.text().strip()

        if not v1_str or not v2_str:
            QMessageBox.warning(self, "Warning", "Please select both Version 1 and Version 2 folders.")
            return

        from core.version_diff import AssetVersionComparator
        out_path = Path(diff_out_str) if diff_out_str else None
        try:
            report = AssetVersionComparator.compare_directories(Path(v1_str), Path(v2_str), out_path)
            s = report["summary"]
            msg = (
                f"Version Diff Completed!\n"
                f"  - Total V1: {s['total_v1']}\n"
                f"  - Total V2: {s['total_v2']}\n"
                f"  - Added: {s['added_count']}\n"
                f"  - Deleted: {s['deleted_count']}\n"
                f"  - Modified: {s['modified_count']}\n"
                f"  - Identical: {s['identical_count']}\n"
            )
            self.diff_log_text.setPlainText(msg)
            QMessageBox.information(self, "Diff Summary", msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Diff failed: {e}")

    def _run_upscale(self) -> None:
        img_str = self.up_file_edit.text().strip()
        if not img_str:
            QMessageBox.warning(self, "Warning", "Please select an image file.")
            return

        from extractors.media_pipeline import TextureUpscaler
        p = Path(img_str)
        out_p = p.parent / f"{p.stem}_{self.scale_spin.value()}x{p.suffix}"
        try:
            res = TextureUpscaler.upscale_image(p, out_p, scale=self.scale_spin.value())
            QMessageBox.information(self, "Success", f"Upscaled image saved to:\n{res}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Upscale failed: {e}")

    def _run_clean_alpha(self) -> None:
        img_str = self.up_file_edit.text().strip()
        if not img_str:
            QMessageBox.warning(self, "Warning", "Please select an image file.")
            return

        from extractors.media_pipeline import SpriteCleaner
        p = Path(img_str)
        out_p = p.parent / f"{p.stem}_clean{p.suffix}"
        try:
            res = SpriteCleaner.clean_transparency(p, out_p)
            QMessageBox.information(self, "Success", f"Cleaned sprite saved to:\n{res}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Alpha cleaning failed: {e}")

    def _refresh_plugins(self) -> None:
        self.plugin_list_widget.clear()
        plugins = PluginRegistry.list_plugins()
        for p in plugins:
            self.plugin_list_widget.addItem(f"{p['name']} v{p['version']} - {p['description']} (By {p['author']})")
