import sqlite3
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

import config
from ui.main_window import Sayte


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(config.NAME)
    app.setWindowIcon(QIcon(str(config.ICON_PATH)))
    app.setQuitOnLastWindowClosed(False)
    try:
        window = Sayte()
    except (OSError, sqlite3.Error) as error:
        QMessageBox.critical(
            None, "Sayte", f"Не удалось открыть базу заметок: {error}"
        )
        sys.exit(1)
    try:
        from utils.hotkey import Hotkey

        window.hotkey = Hotkey(config.HOTKEY)
        window.hotkey.activated.connect(
            window.toggleRecording, Qt.ConnectionType.QueuedConnection
        )
        app.aboutToQuit.connect(window.hotkey.stop)
        window.hotkey.start()
    except (OSError, ImportError, ValueError) as error:
        QMessageBox.warning(
            window, "Горячая клавиша",
            f"Не удалось включить {config.HOTKEY}: {error}"
        )
    window.show()
    sys.exit(app.exec())
