from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget

import config


class VoiceWave(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.levels = [0.0] * config.WAVE_LEVEL_COUNT

    def addLevel(self, level):
        self.levels = self.levels[1:] + [min(level * config.WAVE_SCALE, 1.0)]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(config.WAVE_COLOR))
        step = self.width() / len(self.levels)
        for index, level in enumerate(self.levels):
            height = config.WAVE_MIN_HEIGHT + level * (
                self.height() - config.WAVE_MIN_HEIGHT
            )
            painter.drawRoundedRect(
                QRectF(
                    index * step + 1,
                    (self.height() - height) / 2,
                    max(1, step - config.WAVE_BAR_GAP),
                    height,
                ),
                config.WAVE_RADIUS,
                config.WAVE_RADIUS,
            )
