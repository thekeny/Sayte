import sqlite3

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox, QPushButton

import config
from ai.presets import getBuiltinPresets


class PresetWindow(QDialog):
    def __init__(self, presets, parent=None):
        super().__init__(parent)
        self.presets = presets
        self.initUI()

    def initUI(self):
        uic.loadUi(config.PRESET_UI_PATH, self)
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
        self.presetCombo.currentIndexChanged.connect(self.changePreset)
        self.savePresetButton.clicked.connect(self.savePreset)
        self.deletePresetButton.clicked.connect(self.deletePreset)
        self.closeButton.clicked.connect(self.accept)
        self.loadPresets()

    def loadPresets(self, selected=None):
        rows = self.presets.getPresets()
        self.presetCombo.blockSignals(True)
        self.presetCombo.clear()
        self.presetCombo.addItem("Новое действие", None)
        for preset in getBuiltinPresets():
            self.presetCombo.addItem(preset["name"], preset)
        selectedIndex = 0
        for row in rows:
            self.presetCombo.addItem(row["name"], row)
            if row["id"] == selected:
                selectedIndex = self.presetCombo.count() - 1
        self.presetCombo.setCurrentIndex(selectedIndex)
        self.presetCombo.blockSignals(False)
        self.changePreset()

    def changePreset(self):
        preset = self.presetCombo.currentData()
        self.promptInput.setPlainText(preset["prompt"] if preset else "")
        custom = preset is not None and preset["id"] is not None
        self.presetName.setText(preset["name"] if custom else "")
        self.deletePresetButton.setEnabled(custom)

    def savePreset(self):
        preset = self.presetCombo.currentData()
        presetId = preset["id"] if preset else None
        try:
            presetId = self.presets.savePreset(
                presetId,
                self.presetName.text(),
                self.promptInput.toPlainText(),
            )
            self.loadPresets(presetId)
        except (sqlite3.Error, ValueError) as error:
            self.statusLabel.setText(f"Не удалось сохранить режим: {error}")

    def deletePreset(self):
        preset = self.presetCombo.currentData()
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
            self.presets.deletePreset(preset["id"])
            self.loadPresets()
        except sqlite3.Error:
            self.statusLabel.setText("Не удалось удалить режим из базы.")
