from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor, QIcon
from PyQt6.QtWidgets import QApplication, QWidget

import config


class RecordingWindow(QWidget):
    stopRequested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.busy = False
        self.initUI()

    def initUI(self):
        path = Path(__file__).with_suffix(".ui")
        uic.loadUi(str(path), self)
        self.setWindowFlags(
            Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowIcon(QIcon(str(config.ICON_PATH)))
        self.stopButton.clicked.connect(self.stopRequested.emit)
        self.hideTimer = QTimer(self)
        self.hideTimer.setSingleShot(True)
        self.hideTimer.timeout.connect(self.hide)

    def setState(self, state, text):
        self.hideTimer.stop()
        self.busy = state in ("recording", "processing")
        self.label.setText(text)
        self.stopButton.setVisible(state == "recording")
        screen = QApplication.screenAt(QCursor.pos())
        if screen is None:
            screen = QApplication.primaryScreen()
        geometry = screen.availableGeometry()
        self.move(geometry.right() - self.width() - 15,
                  geometry.bottom() - self.height() - 15)
        self.show()
        if not self.busy:
            self.hideTimer.start(3000)

    def closeEvent(self, event):
        if self.busy:
            event.ignore()
        else:
            event.accept()
