import sqlite3

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit
from PyQt6.QtWidgets import QPushButton, QVBoxLayout
from PyQt6.QtWidgets import QMessageBox

import config


class HotkeyDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.shortcut = ""
        self.setWindowTitle("Назначить сочетание")
        self.resize(400, 140)
        layout = QVBoxLayout(self)
        self.hint = QLabel(
            "Нажмите сочетание с Ctrl, Alt, Shift или Win\n"
            "и буквой A–Z или цифрой 0–9. Esc — отмена.", self
        )
        layout.addWidget(self.hint)
        cancelButton = QPushButton("Отмена", self)
        cancelButton.clicked.connect(self.reject)
        layout.addWidget(cancelButton)

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
        self.setWindowTitle("Настройки Sayte")
        self.resize(400, 180)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Горячая клавиша записи:", self))
        self.hotkeyInput = QLineEdit(window.shortcut, self)
        self.hotkeyInput.setReadOnly(True)
        layout.addWidget(self.hotkeyInput)
        self.assignButton = QPushButton("Назначить сочетание", self)
        self.assignButton.clicked.connect(self.assignHotkey)
        layout.addWidget(self.assignButton)
        self.resetButton = QPushButton("Сбросить", self)
        self.resetButton.clicked.connect(self.resetSettings)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel, self
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setText(
            "Сохранить"
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            "Отмена"
        )
        self.buttons.accepted.connect(self.saveSettings)
        self.buttons.rejected.connect(self.reject)
        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(self.resetButton)
        buttonsLayout.addWidget(self.buttons)
        layout.addLayout(buttonsLayout)

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
