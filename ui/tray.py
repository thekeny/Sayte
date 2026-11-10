from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

import config


class Tray(QSystemTrayIcon):
    def __init__(self, window):
        super().__init__(QIcon(config.ICON_PATH), window)
        self.window = window
        self.setToolTip(config.NAME)
        self.menu = QMenu(window)
        self.open_action = QAction("Открыть", self)
        self.open_action.triggered.connect(window.show_window)
        self.menu.addAction(self.open_action)
        self.record_action = QAction("Начать запись", self)
        self.record_action.triggered.connect(window.toggle_recording)
        self.menu.addAction(self.record_action)
        self.menu.addSeparator()
        self.exit_action = QAction("Выход", self)
        self.exit_action.triggered.connect(window.request_exit)
        self.menu.addAction(self.exit_action)
        self.setContextMenu(self.menu)
        self.activated.connect(self.open_window)

    def open_window(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.window.show_window()

    def set_state(self, state, text):
        self.setToolTip(f"{config.NAME}: {text}")
        self.record_action.setEnabled(state != "processing")
        self.record_action.setText(config.RECORD_BUTTON_TITLES[state])
