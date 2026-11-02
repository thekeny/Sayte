from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QPainter, QPen, QPalette
from PyQt6.QtWidgets import QWidget

import config


class Spinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.setInterval(config.SPINNER_INTERVAL_MS)
        self.timer.timeout.connect(self.advance)

    def advance(self):
        self.angle = (self.angle + config.SPINNER_STEP) % 360
        self.update()

    def showEvent(self, event):
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self.palette().color(QPalette.ColorRole.WindowText), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        side = min(self.width(), self.height()) - 6
        rect = QRectF((self.width() - side) / 2,
                      (self.height() - side) / 2, side, side)
        painter.drawArc(rect, -self.angle * 16, config.SPINNER_ARC * 16)
