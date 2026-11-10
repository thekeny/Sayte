import sqlite3

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox, QPushButton

import config
from ai.presets import get_builtin_presets


class PresetWindow(QDialog):
    def __init__(self, presets, parent=None):
        super().__init__(parent)
        self.presets = presets
        self.init_ui()

    def init_ui(self):
        uic.loadUi(config.PRESET_UI_PATH, self)
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
        self.preset_combo.currentIndexChanged.connect(self.change_preset)
        self.save_preset_button.clicked.connect(self.save_preset)
        self.delete_preset_button.clicked.connect(self.delete_preset)
        self.close_button.clicked.connect(self.accept)
        self.load_presets()

    def load_presets(self, selected=None):
        rows = self.presets.get_presets()
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("Новое действие", None)
        for preset in get_builtin_presets():
            self.preset_combo.addItem(preset["name"], preset)
        selected_index = 0
        for row in rows:
            self.preset_combo.addItem(row["name"], row)
            if row["id"] == selected:
                selected_index = self.preset_combo.count() - 1
        self.preset_combo.setCurrentIndex(selected_index)
        self.preset_combo.blockSignals(False)
        self.change_preset()

    def change_preset(self):
        preset = self.preset_combo.currentData()
        self.prompt_input.setPlainText(preset["prompt"] if preset else "")
        custom = preset is not None and preset["id"] is not None
        self.preset_name.setText(preset["name"] if custom else "")
        self.delete_preset_button.setEnabled(custom)

    def save_preset(self):
        preset = self.preset_combo.currentData()
        preset_id = preset["id"] if preset else None
        try:
            preset_id = self.presets.save_preset(
                preset_id,
                self.preset_name.text(),
                self.prompt_input.toPlainText(),
            )
            self.load_presets(preset_id)
        except (sqlite3.Error, ValueError) as error:
            self.status_label.setText(f"Не удалось сохранить режим: {error}")

    def delete_preset(self):
        preset = self.preset_combo.currentData()
        if not preset or preset["id"] is None:
            return
        answer = QMessageBox.question(
            self,
            "Режим обработки",
            "Удалить выбранный режим?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.presets.delete_preset(preset["id"])
            self.load_presets()
        except sqlite3.Error:
            self.status_label.setText("Не удалось удалить режим из базы.")
