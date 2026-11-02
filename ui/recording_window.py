from PyQt6 import uic
from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor, QIcon
from PyQt6.QtWidgets import QApplication, QWidget

import config


class RecordingWindow(QWidget):
    stopRequested = pyqtSignal()

    def __init__(self, recorder):
        super().__init__()
        self.recorder = recorder
        self.busy = False
        self.initUI()

    def initUI(self):
        uic.loadUi(config.RECORDING_UI_PATH, self)
        self.setWindowIcon(QIcon(config.ICON_PATH))
        self.setWindowFlags(
            Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint
        )
        self.stopButton.clicked.connect(self.stopRequested.emit)
        self.waveTimer = QTimer(self)
        self.waveTimer.setInterval(config.WAVE_INTERVAL_MS)
        self.waveTimer.timeout.connect(self.updateWave)
        self.hideTimer = QTimer(self)
        self.hideTimer.setSingleShot(True)
        self.hideTimer.timeout.connect(self.hide)

    def setState(self, state, text):
        self.hideTimer.stop()
        self.busy = state in ("recording", "processing")
        self.label.setText(text)
        self.stopButton.setVisible(state == "recording")
        self.wave.setVisible(state == "recording")
        if state == "recording":
            self.wave.levels = [0.0] * config.WAVE_LEVEL_COUNT
            self.waveTimer.start()
        else:
            self.waveTimer.stop()
        screen = QApplication.screenAt(QCursor.pos())
        if screen is None:
            screen = QApplication.primaryScreen()
        geometry = screen.availableGeometry()
        self.show()
        frame = self.frameGeometry()
        margin = config.WINDOW_MARGIN
        frame.moveBottomRight(geometry.bottomRight() - QPoint(margin, margin))
        self.move(frame.topLeft())
        if not self.busy:
            self.hideTimer.start(config.HIDE_MESSAGE_MS)

    def updateWave(self):
        self.wave.addLevel(self.recorder.level)

    def closeEvent(self, event):
        if self.busy:
            event.ignore()
        else:
            event.accept()
