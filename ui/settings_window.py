import sqlite3

from PyQt6 import uic
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import QDialog, QMessageBox

import config


class HotkeyDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.shortcut = ""
        self.initUI()

    def initUI(self):
        uic.loadUi(config.HOTKEY_UI_PATH, self)
        self.cancelButton.clicked.connect(self.reject)

    def event(self, event):
        if event.type() == QEvent.Type.ShortcutOverride:
            event.accept()
            return True
        return super().event(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        if event.isAutoRepeat():
            return
        if event.key() in (
            Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift,
            Qt.Key.Key_Meta, Qt.Key.Key_AltGr
        ):
            return
        key = event.nativeVirtualKey() or event.key()
        modifiers = []
        for flag, name in (
            (Qt.KeyboardModifier.ControlModifier, "ctrl"),
            (Qt.KeyboardModifier.AltModifier, "alt"),
            (Qt.KeyboardModifier.ShiftModifier, "shift"),
            (Qt.KeyboardModifier.MetaModifier, "win")
        ):
            if event.modifiers() & flag:
                modifiers.append(name)
        if not modifiers or not (65 <= key <= 90 or 48 <= key <= 57):
            self.hint.setText(
                "Нужно сочетание с Ctrl, Alt, Shift или Win\n"
                "и буквой A–Z или цифрой 0–9. Esc — отмена."
            )
            return
        self.shortcut = "+".join(modifiers + [chr(key).lower()])
        self.accept()


class SettingsWindow(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.initUI()

    def initUI(self):
        uic.loadUi(config.SETTINGS_UI_PATH, self)
        self.hotkeyInput.setText(self.window.shortcut)
        self.assignButton.clicked.connect(self.assignHotkey)
        self.resetButton.clicked.connect(self.resetSettings)
        self.saveButton.clicked.connect(self.saveSettings)
        self.cancelButton.clicked.connect(self.reject)

    def assignHotkey(self):
        hotkey = self.window.hotkey
        resume = hotkey is not None and hotkey.registered
        if resume:
            hotkey.stop()
        try:
            dialog = HotkeyDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.hotkeyInput.setText(dialog.shortcut)
        finally:
            if resume:
                try:
                    hotkey.start()
                except (OSError, ValueError) as error:
                    QMessageBox.warning(self, "Горячая клавиша", str(error))

    def resetSettings(self):
        answer = QMessageBox.question(
            self, "Сброс настроек", "Вернуть горячую клавишу по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.hotkeyInput.setText(config.HOTKEY)

    def saveSettings(self):
        shortcut = self.hotkeyInput.text().replace(" ", "").lower()
        try:
            self.window.applySettings(shortcut)
        except (OSError, ImportError, ValueError, sqlite3.Error) as error:
            QMessageBox.warning(self, "Настройки", str(error))
            return
        self.accept()
