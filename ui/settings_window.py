import sqlite3

from PyQt6 import uic
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

import config
from ui.theme import apply_theme
from utils.autostart import get_autostart, get_command, set_autostart
from ui.provider_window import ProviderWindow
from ui.preset_window import PresetWindow


class HotkeyDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.shortcut = ""
        self.init_ui()

    def init_ui(self):
        uic.loadUi(config.HOTKEY_UI_PATH, self)
        self.cancel_button.clicked.connect(self.reject)

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
        self.init_ui()

    def init_ui(self):
        uic.loadUi(config.SETTINGS_UI_PATH, self)
        self.theme_combo.addItem("Светлая", "light")
        self.theme_combo.addItem("Тёмная", "dark")
        self.theme_combo.setCurrentIndex(
            self.theme_combo.findData(self.window.settings.get_theme())
        )
        self.autostart_check.setChecked(bool(get_autostart()))
        self.font_size_spin.setRange(
            config.NOTE_FONT_MIN, config.NOTE_FONT_MAX
        )
        self.font_size_spin.setValue(self.window.settings.get_font_size())
        self.hotkey_input.setText(self.window.shortcut)
        self.providers_button.setIcon(QIcon(config.CPU_ICON_PATH))
        self.providers_button.clicked.connect(self.open_providers)
        self.presets_button.clicked.connect(self.open_presets)
        self.assign_button.clicked.connect(self.assign_hotkey)
        for role, title in (
            (QDialogButtonBox.StandardButton.Save, "Сохранить"),
            (QDialogButtonBox.StandardButton.Cancel, "Отмена"),
            (QDialogButtonBox.StandardButton.RestoreDefaults, "Сбросить"),
        ):
            self.button_box.button(role).setText(title)
        self.button_box.button(
            QDialogButtonBox.StandardButton.RestoreDefaults
        ).clicked.connect(self.reset_settings)
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.reject)

    def open_providers(self):
        try:
            ProviderWindow(self.window.providers, self).exec()
        except sqlite3.Error:
            QMessageBox.warning(
                self, "Подключения ИИ", "Не удалось загрузить подключения."
            )

    def open_presets(self):
        try:
            PresetWindow(self.window.presets, self).exec()
        except sqlite3.Error:
            QMessageBox.warning(self, "Действия ИИ", "Ошибка чтения действий.")

    def assign_hotkey(self):
        hotkey = self.window.hotkey
        resume = hotkey is not None and hotkey.registered
        if resume:
            hotkey.stop()
        try:
            dialog = HotkeyDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.hotkey_input.setText(dialog.shortcut)
        finally:
            if resume:
                try:
                    hotkey.start()
                except (OSError, ValueError) as error:
                    QMessageBox.warning(self, "Горячая клавиша", str(error))

    def reset_settings(self):
        answer = QMessageBox.question(
            self,
            "Сброс настроек",
            "Вернуть настройки по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.hotkey_input.setText(config.HOTKEY)
            self.theme_combo.setCurrentIndex(0)
            self.autostart_check.setChecked(False)
            self.font_size_spin.setValue(config.NOTE_FONT_SIZE)

    def save_settings(self):
        shortcut = self.hotkey_input.text().replace(" ", "").lower()
        try:
            previous = self.window.shortcut
            old_theme = self.window.settings.get_theme()
            old_font_size = self.window.settings.get_font_size()
            old_command = get_autostart()
        except (OSError, sqlite3.Error) as error:
            QMessageBox.warning(self, "Настройки", str(error))
            return
        theme = self.theme_combo.currentData()
        try:
            command = (
                get_command() if self.autostart_check.isChecked() else None
            )
            if command != old_command:
                set_autostart(command)
            self.window.apply_settings(shortcut)
            self.window.settings.save_theme(theme)
            self.window.settings.save_font_size(self.font_size_spin.value())
            apply_theme(theme)
        except (OSError, ImportError, ValueError, sqlite3.Error) as error:
            for restore in (
                lambda: set_autostart(old_command),
                lambda: self.window.apply_settings(previous),
                lambda: self.window.settings.save_theme(old_theme),
                lambda: self.window.settings.save_font_size(old_font_size),
                lambda: apply_theme(old_theme),
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
