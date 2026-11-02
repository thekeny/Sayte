import os
import sqlite3
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

import config
from ui.main_window import Sayte
from ui.theme import applyTheme


if __name__ == "__main__":
    location = sys.executable if getattr(sys, "frozen", False) else __file__
    os.chdir(os.path.dirname(os.path.abspath(location)))
    app = QApplication(sys.argv)
    app.setApplicationName(config.NAME)
    app.setWindowIcon(QIcon(config.ICON_PATH))
    app.setQuitOnLastWindowClosed(False)
    try:
        window = Sayte()
    except (OSError, sqlite3.Error) as error:
        QMessageBox.critical(
            None, "Sayte", f"Не удалось открыть базу заметок: {error}"
        )
        sys.exit(1)
    try:
        window.startHotkey()
    except (OSError, ImportError, ValueError) as error:
        QMessageBox.warning(
            window,
            "Горячая клавиша",
            f"Не удалось включить {window.shortcut}: {error}",
        )
    app.aboutToQuit.connect(
        lambda: window.hotkey.stop() if window.hotkey is not None else None
    )
    applyTheme(window.settings.getTheme())
    if "--start-in-tray" not in sys.argv or not window.tray.isVisible():
        window.show()
    sys.exit(app.exec())
