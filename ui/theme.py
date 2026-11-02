from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

import config


def applyTheme(theme):
    app = QApplication.instance()
    app.setStyle("Fusion")
    background, surface, text, muted, border, selected = config.THEME_COLORS[theme]
    palette = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, background),
        (QPalette.ColorRole.Base, surface),
        (QPalette.ColorRole.AlternateBase, background),
        (QPalette.ColorRole.WindowText, text),
        (QPalette.ColorRole.Text, text),
        (QPalette.ColorRole.Button, surface),
        (QPalette.ColorRole.ButtonText, text),
        (QPalette.ColorRole.Highlight, selected),
        (QPalette.ColorRole.HighlightedText, text),
        (QPalette.ColorRole.ToolTipBase, surface),
        (QPalette.ColorRole.ToolTipText, text)
    ):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(f"""
        QWidget {{ color: {text}; }}
        QDialog, QWidget#Sayte {{ background: {background}; }}
        QPushButton, QToolButton, QLineEdit, QTextEdit, QComboBox {{
            background: {surface}; border: 1px solid {border};
            border-radius: 6px; padding: 6px;
        }}
        QPushButton:hover, QToolButton:hover, QToolButton:checked {{
            background: {selected};
        }}
        QWidget:disabled {{ color: {muted}; }}
        QLineEdit:focus, QTextEdit:focus, QPushButton:focus {{
            border: 1px solid {text};
        }}
        QListWidget {{ border: none; background: transparent; }}
        QListWidget::item {{
            background: {surface}; border: 1px solid {border};
            border-radius: 8px;
        }}
        QListWidget::item:selected {{ background: {selected}; }}
        QLabel#titleLabel, QLabel#heading {{ font-weight: bold; }}
        QLabel#previewLabel, QLabel#tagsLabel {{ color: {muted}; }}
        QMenu {{ background: {surface}; }}
        QMenu::item:selected {{ background: {selected}; }}
    """)
