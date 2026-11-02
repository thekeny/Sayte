from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import QPoint, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QIcon, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

import config


class VoiceWave(QWidget):
    def __init__(self):
        super().__init__()
        self.levels = [0.0] * 32
        self.setFixedHeight(36)

    def addLevel(self, level):
        self.levels = self.levels[1:] + [min(level * 8, 1.0)]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#6c63ff"))
        step = self.width() / len(self.levels)
        for index, level in enumerate(self.levels):
            height = 4 + level * (self.height() - 4)
            painter.drawRoundedRect(
                QRectF(index * step + 1, (self.height() - height) / 2,
                       max(1, step - 3), height), 2, 2
            )


class RecordingWindow(QWidget):
    stopRequested = pyqtSignal()

    def __init__(self, recorder):
        super().__init__()
        self.recorder = recorder
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
        self.wave = VoiceWave()
        self.verticalLayout.insertWidget(1, self.wave)
        self.waveTimer = QTimer(self)
        self.waveTimer.setInterval(80)
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
            self.wave.levels = [0.0] * 32
            self.waveTimer.start()
        else:
            self.waveTimer.stop()
        screen = QApplication.screenAt(QCursor.pos())
        if screen is None:
            screen = QApplication.primaryScreen()
        geometry = screen.availableGeometry()
        self.show()
        frame = self.frameGeometry()
        frame.moveBottomRight(geometry.bottomRight() - QPoint(15, 15))
        self.move(frame.topLeft())
        if not self.busy:
            self.hideTimer.start(3000)

    def updateWave(self):
        self.wave.addLevel(self.recorder.level)

    def closeEvent(self, event):
        if self.busy:
            event.ignore()
        else:
            event.accept()
