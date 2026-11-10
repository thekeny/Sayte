from PyQt6 import uic
from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor, QIcon
from PyQt6.QtWidgets import QApplication, QWidget

import config


class RecordingWindow(QWidget):
    stop_requested = pyqtSignal()

    def __init__(self, recorder):
        super().__init__()
        self.recorder = recorder
        self.busy = False
        self.init_ui()

    def init_ui(self):
        uic.loadUi(config.RECORDING_UI_PATH, self)
        self.setWindowIcon(QIcon(config.ICON_PATH))
        self.setWindowFlags(
            Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint
        )
        self.spinner.hide()
        self.download_label.hide()
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.wave_timer = QTimer(self)
        self.wave_timer.setInterval(config.WAVE_INTERVAL_MS)
        self.wave_timer.timeout.connect(self.update_wave)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def set_state(self, state, text):
        self.hide_timer.stop()
        self.busy = state in ("recording", "processing")
        processing = state == "processing"
        self.label.setText(config.PROCESSING_TEXT if processing else text)
        self.spinner.setVisible(processing)
        downloading = processing and text == config.MODEL_DOWNLOAD_TEXT
        self.download_label.setText(config.MODEL_DOWNLOAD_TEXT)
        self.download_label.setVisible(downloading)
        self.stop_button.setVisible(state == "recording")
        self.wave.setVisible(state == "recording")
        if state == "recording":
            self.wave.levels = [0.0] * config.WAVE_LEVEL_COUNT
            self.wave_timer.start()
        else:
            self.wave_timer.stop()
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
            self.hide_timer.start(config.HIDE_MESSAGE_MS)

    def update_wave(self):
        self.wave.add_level(self.recorder.level)

    def closeEvent(self, event):
        if self.busy:
            event.ignore()
        else:
            event.accept()
