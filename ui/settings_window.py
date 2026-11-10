import sqlite3

from PyQt6 import uic
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

import config
from ui.theme import applyTheme
from utils.autostart import getAutostart, getCommand, setAutostart
from ui.provider_window import ProviderWindow
from ui.preset_window import PresetWindow


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
            Qt.Key.Key_Control,
            Qt.Key.Key_Alt,
            Qt.Key.Key_Shift,
            Qt.Key.Key_Meta,
            Qt.Key.Key_AltGr,
        ):
            return
        key = event.nativeVirtualKey() or event.key()
        modifiers = []
        for flag, name in (
            (Qt.KeyboardModifier.ControlModifier, "ctrl"),
            (Qt.KeyboardModifier.AltModifier, "alt"),
            (Qt.KeyboardModifier.ShiftModifier, "shift"),
            (Qt.KeyboardModifier.MetaModifier, "win"),
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
        self.themeCombo.addItem("Светлая", "light")
        self.themeCombo.addItem("Тёмная", "dark")
        self.themeCombo.setCurrentIndex(
            self.themeCombo.findData(self.window.settings.getTheme())
        )
        self.autostartCheck.setChecked(bool(getAutostart()))
        self.fontSizeSpin.setRange(config.NOTE_FONT_MIN, config.NOTE_FONT_MAX)
        self.fontSizeSpin.setValue(self.window.settings.getFontSize())
        self.hotkeyInput.setText(self.window.shortcut)
        self.providersButton.setIcon(QIcon(config.CPU_ICON_PATH))
        self.providersButton.clicked.connect(self.openProviders)
        self.presetsButton.clicked.connect(self.openPresets)
        self.assignButton.clicked.connect(self.assignHotkey)
        for role, title in (
            (QDialogButtonBox.StandardButton.Save, "Сохранить"),
            (QDialogButtonBox.StandardButton.Cancel, "Отмена"),
            (QDialogButtonBox.StandardButton.RestoreDefaults, "Сбросить"),
        ):
            self.buttonBox.button(role).setText(title)
        self.buttonBox.button(
            QDialogButtonBox.StandardButton.RestoreDefaults
        ).clicked.connect(self.resetSettings)
        self.buttonBox.accepted.connect(self.saveSettings)
        self.buttonBox.rejected.connect(self.reject)

    def openProviders(self):
        try:
            ProviderWindow(self.window.providers, self).exec()
        except sqlite3.Error:
            QMessageBox.warning(
                self, "Подключения ИИ", "Не удалось загрузить подключения."
            )

    def openPresets(self):
        try:
            PresetWindow(self.window.presets, self).exec()
        except sqlite3.Error:
            QMessageBox.warning(self, "Действия ИИ", "Ошибка чтения действий.")

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
            self,
            "Сброс настроек",
            "Вернуть настройки по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.hotkeyInput.setText(config.HOTKEY)
            self.themeCombo.setCurrentIndex(0)
            self.autostartCheck.setChecked(False)
            self.fontSizeSpin.setValue(config.NOTE_FONT_SIZE)

    def saveSettings(self):
        shortcut = self.hotkeyInput.text().replace(" ", "").lower()
        try:
            previous = self.window.shortcut
            oldTheme = self.window.settings.getTheme()
            oldFontSize = self.window.settings.getFontSize()
            oldCommand = getAutostart()
        except (OSError, sqlite3.Error) as error:
            QMessageBox.warning(self, "Настройки", str(error))
            return
        theme = self.themeCombo.currentData()
        try:
            command = getCommand() if self.autostartCheck.isChecked() else None
            if command != oldCommand:
                setAutostart(command)
            self.window.applySettings(shortcut)
            self.window.settings.saveTheme(theme)
            self.window.settings.saveFontSize(self.fontSizeSpin.value())
            applyTheme(theme)
        except (OSError, ImportError, ValueError, sqlite3.Error) as error:
            for restore in (
                lambda: setAutostart(oldCommand),
                lambda: self.window.applySettings(previous),
                lambda: self.window.settings.saveTheme(oldTheme),
                lambda: self.window.settings.saveFontSize(oldFontSize),
                lambda: applyTheme(oldTheme),
            ):
                try:
                    restore()
                except (
                    OSError,
                    ImportError,
                    ValueError,
                    sqlite3.Error,
                ) as issue:
                    QMessageBox.warning(self, "Восстановление", str(issue))
            QMessageBox.warning(self, "Настройки", str(error))
            return
        self.accept()
