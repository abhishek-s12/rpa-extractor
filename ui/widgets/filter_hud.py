"""Smart Search & Filter HUD Bar Component.

Provides dynamic query input, preset management dropdown, and active filter signals.
"""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QPushButton, QWidget
from core.smart_filter import PresetManager


class FilterHudBar(QFrame):
    """Filter HUD bar for quick asset filtering and saved preset selection."""

    filterChanged = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.preset_mgr = PresetManager()
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        hud_lbl = QLabel("Search HUD:")
        hud_lbl.setStyleSheet("font-weight: bold; color: #38bdf8;")

        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Filter assets e.g. 'width > 1920', 'duration > 60', 'size > 2MB', 'cat:audio'...")
        self.query_input.textChanged.connect(self._on_text_changed)

        # Preset Dropdown
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(150)
        self._refresh_presets()
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)

        save_preset_btn = QPushButton("Save Preset")
        save_preset_btn.setObjectName("SecondaryBtn")
        save_preset_btn.clicked.connect(self._save_preset)

        del_preset_btn = QPushButton("Delete")
        del_preset_btn.setObjectName("SecondaryBtn")
        del_preset_btn.clicked.connect(self._delete_preset)

        layout.addWidget(hud_lbl)
        layout.addWidget(self.query_input, 1)
        layout.addWidget(QLabel("Presets:"))
        layout.addWidget(self.preset_combo)
        layout.addWidget(save_preset_btn)
        layout.addWidget(del_preset_btn)

    def _refresh_presets(self) -> None:
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("-- Select Preset --", "")
        for name, query in self.preset_mgr.presets.items():
            self.preset_combo.addItem(name, query)
        self.preset_combo.blockSignals(False)

    def _on_text_changed(self, text: str) -> None:
        self.filterChanged.emit(text)

    def _on_preset_selected(self, index: int) -> None:
        query = self.preset_combo.currentData()
        if query:
            self.query_input.setText(query)

    def _save_preset(self) -> None:
        curr_query = self.query_input.text().strip()
        if not curr_query:
            return
        name, ok = QInputDialog.getText(self, "Save Export Preset", "Preset Name:")
        if ok and name.strip():
            self.preset_mgr.add_preset(name.strip(), curr_query)
            self._refresh_presets()

    def _delete_preset(self) -> None:
        curr_name = self.preset_combo.currentText()
        if curr_name and curr_name != "-- Select Preset --":
            self.preset_mgr.remove_preset(curr_name)
            self._refresh_presets()
