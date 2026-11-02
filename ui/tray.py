from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

import config


class Tray(QSystemTrayIcon):
    def __init__(self, window):
        super().__init__(QIcon(config.ICON_PATH), window)
        self.window = window
        self.setToolTip(config.NAME)
        self.menu = QMenu(window)
        self.openAction = QAction("Открыть", self)
        self.openAction.triggered.connect(window.showWindow)
        self.menu.addAction(self.openAction)
        self.recordAction = QAction("Начать запись", self)
        self.recordAction.triggered.connect(window.toggleRecording)
        self.menu.addAction(self.recordAction)
        self.menu.addSeparator()
        self.exitAction = QAction("Выход", self)
        self.exitAction.triggered.connect(window.requestExit)
        self.menu.addAction(self.exitAction)
        self.setContextMenu(self.menu)
        self.activated.connect(self.openWindow)

    def openWindow(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.window.showWindow()

    def setState(self, state, text):
        self.setToolTip(f"{config.NAME}: {text}")
        self.recordAction.setEnabled(state != "processing")
        self.recordAction.setText(config.RECORD_BUTTON_TITLES[state])
