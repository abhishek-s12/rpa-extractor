"""Ren'Py & Python syntax highlighter module for Qt QTextDocument.

Provides custom color rules for Ren'Py statements (label, show, scene, define),
dialogue strings, comments, and Python syntax.
"""

import re
from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class HighlightingRule:
    """Structure holding regex pattern and matching text format."""

    def __init__(self, pattern: str, char_format: QTextCharFormat) -> None:
        self.pattern = QRegularExpression(pattern)
        self.format = char_format


class RenPySyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Ren'Py (.rpy) script files."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.highlighting_rules: list[HighlightingRule] = []

        # Ren'Py Keyword Format (Purple/Violet)
        renpy_keyword_format = QTextCharFormat()
        renpy_keyword_format.setForeground(QColor("#c084fc"))
        renpy_keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            r"\blabel\b", r"\binit\b", r"\bshow\b", r"\bhide\b", r"\bscene\b",
            r"\bwith\b", r"\bdefine\b", r"\bdefault\b", r"\bimage\b", r"\bplay\b",
            r"\bstop\b", r"\bjump\b", r"\bcall\b", r"\bmenu\b", r"\breturn\b",
            r"\bpass\b", r"\bpython\b", r"\btransform\b", r"\bscreen\b"
        ]
        for kw in keywords:
            self.highlighting_rules.append(HighlightingRule(kw, renpy_keyword_format))

        # Python Control Flow Keywords (Blue)
        py_keyword_format = QTextCharFormat()
        py_keyword_format.setForeground(QColor("#60a5fa"))
        py_keyword_format.setFontWeight(QFont.Bold)
        py_keywords = [
            r"\bif\b", r"\belif\b", r"\belse\b", r"\bfor\b", r"\bwhile\b",
            r"\bin\b", r"\bis\b", r"\band\b", r"\bor\b", r"\bnot\b",
            r"\bdef\b", r"\bclass\b", r"\bimport\b", r"\bfrom\b", r"\bTrue\b", r"\bFalse\b", r"\bNone\b"
        ]
        for kw in py_keywords:
            self.highlighting_rules.append(HighlightingRule(kw, py_keyword_format))

        # Dialogue & String Format (Amber / Orange)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#fbbf24"))
        self.highlighting_rules.append(HighlightingRule(r'"[^"\\]*(\\.[^"\\]*)*"', string_format))
        self.highlighting_rules.append(HighlightingRule(r"'[^'\\]*(\\.[^'\\]*)*'", string_format))

        # Comment Format (Muted Grey / Greenish)
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#64748b"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append(HighlightingRule(r"#.*", comment_format))

        # Label Target / Identifier Format (Cyan)
        label_decl_format = QTextCharFormat()
        label_decl_format.setForeground(QColor("#38bdf8"))
        label_decl_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append(HighlightingRule(r"\blabel\s+([a-zA-Z0-9_]+):", label_decl_format))

        # Numbers Format (Rose / Coral)
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#f43f5e"))
        self.highlighting_rules.append(HighlightingRule(r"\b[0-9]+(?:\.[0-9]+)?\b", number_format))

        # Single-line Python dollar statement ($ var = val) (Emerald)
        dollar_format = QTextCharFormat()
        dollar_format.setForeground(QColor("#34d399"))
        self.highlighting_rules.append(HighlightingRule(r"^\s*\$.*", dollar_format))

    def highlightBlock(self, text: str) -> None:
        """Highlights a single block of text."""
        for rule in self.highlighting_rules:
            match_iterator = rule.pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), rule.format)
