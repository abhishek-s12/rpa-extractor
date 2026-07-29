"""PySide6 Theme & Styling definitions.

Provides premium dark/light mode stylesheets, glassmorphic accents,
font loading, and UI color palettes.
"""

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication


DARK_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #12141a;
    color: #e2e8f0;
}

QWidget {
    font-family: 'Segoe UI', 'Inter', 'Outfit', sans-serif;
    font-size: 13px;
    color: #e2e8f0;
}

QSplitter::handle {
    background-color: #1e2430;
    width: 4px;
    height: 4px;
}

QSplitter::handle:hover {
    background-color: #3b82f6;
}

/* Sidebar & Cards */
QFrame#Sidebar, QFrame#Card {
    background-color: #1a1d26;
    border: 1px solid #262b38;
    border-radius: 8px;
}

QHeaderView::section {
    background-color: #1e222e;
    color: #94a3b8;
    padding: 6px;
    border: none;
    font-weight: bold;
}

QTreeWidget, QTableWidget, QListWidget {
    background-color: #161922;
    border: 1px solid #262b38;
    border-radius: 6px;
    gridline-color: #262b38;
    color: #e2e8f0;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

QTreeWidget::item:hover, QTableWidget::item:hover {
    background-color: #222736;
}

/* Buttons */
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #1d4ed8;
}

QPushButton:pressed {
    background-color: #1e40af;
}

QPushButton:disabled {
    background-color: #334155;
    color: #64748b;
}

QPushButton#SecondaryBtn {
    background-color: #334155;
    color: #f1f5f9;
}

QPushButton#SecondaryBtn:hover {
    background-color: #475569;
}

/* Inputs */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {
    background-color: #0f1117;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f8fafc;
    selection-background-color: #2563eb;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #3b82f6;
}

/* Combo Box */
QComboBox {
    background-color: #1e222e;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f8fafc;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #1e222e;
    selection-background-color: #2563eb;
    color: #f8fafc;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #262b38;
    border-radius: 8px;
    background-color: #1a1d26;
    top: -1px;
}

QTabBar::tab {
    background-color: #161922;
    color: #94a3b8;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1a1d26;
    color: #3b82f6;
    font-weight: bold;
    border-bottom: 2px solid #3b82f6;
}

/* Progress Bar */
QProgressBar {
    background-color: #0f1117;
    border: 1px solid #262b38;
    border-radius: 6px;
    text-align: center;
    color: #f8fafc;
}

QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 5px;
}

/* Status Bar */
QStatusBar {
    background-color: #161922;
    color: #94a3b8;
    border-top: 1px solid #262b38;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #12141a;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


def apply_theme(app: QApplication, dark_mode: bool = True) -> None:
    """Applies the selected theme to the PySide6 Application instance."""
    if dark_mode:
        app.setStyleSheet(DARK_STYLESHEET)

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(18, 20, 26))
        palette.setColor(QPalette.WindowText, QColor(226, 232, 240))
        palette.setColor(QPalette.Base, QColor(15, 17, 23))
        palette.setColor(QPalette.AlternateBase, QColor(26, 29, 38))
        palette.setColor(QPalette.ToolTipBase, QColor(226, 232, 240))
        palette.setColor(QPalette.ToolTipText, QColor(226, 232, 240))
        palette.setColor(QPalette.Text, QColor(248, 250, 252))
        palette.setColor(QPalette.Button, QColor(37, 99, 235))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Highlight, QColor(37, 99, 235))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        app.setPalette(palette)
