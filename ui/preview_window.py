import sqlite3

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox, QPushButton

import config
from ai.presets import getBuiltinPresets
from ai.worker import AiWorker


class PreviewWindow(QDialog):
    def __init__(self, providers, presets, text, parent=None):
        super().__init__(parent)
        self.providers = providers
        self.presets = presets
        self.text = text
        self.worker = None
        self.resultReady = False
        self.initUI()

    def initUI(self):
        uic.loadUi(config.PREVIEW_UI_PATH, self)
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
        self.sourceEditor.setPlainText(self.text)
        self.applyButton.setVisible(False)
        self.presetCombo.currentIndexChanged.connect(self.changePreset)
        self.loadActions()
        self.runButton.clicked.connect(self.processText)
        self.applyButton.clicked.connect(self.applyResult)
        self.cancelButton.clicked.connect(self.reject)
        self.resultEditor.textChanged.connect(self.updateApplyButton)

    def loadActions(self):
        for preset in getBuiltinPresets() + self.presets.getPresets():
            self.presetCombo.addItem(preset["name"], preset)
        self.presetCombo.addItem("Свой запрос", None)
        self.changePreset()

    def changePreset(self):
        preset = self.presetCombo.currentData()
        self.promptInput.setPlainText(preset["prompt"] if preset else "")
        self.promptInput.setVisible(preset is None)
        self.promptLabel.setVisible(preset is None)

    def currentProfile(self):
        activeId = self.providers.getActiveProfile()
        profiles = self.providers.getProfiles()
        profile = next((row for row in profiles if row["id"] == activeId), None)
        if profile is None or not profile["model"]:
            raise ValueError(
                "Выберите подключение и модель в настройках → Подключения ИИ."
            )
        self.providers.validateProfile(profile)
        return profile

    def processText(self):
        if self.worker is not None:
            return
        try:
            profile = self.currentProfile()
            if (not profile["model"]
                    or not self.promptInput.toPlainText().strip()):
                raise ValueError("Укажите модель и промпт.")
            if not self.text.strip():
                raise ValueError("Текст заметки пуст.")
            if profile["kind"] == "openrouter" and not profile["api_key"]:
                raise ValueError("Укажите API-ключ в подключениях.")
        except (sqlite3.Error, ValueError) as error:
            self.statusLabel.setText(str(error))
            return
        self.resultReady = False
        self.resultEditor.clear()
        self.startRequest(profile)

    def startRequest(self, profile):
        self.controls.setEnabled(False)
        self.cancelButton.setEnabled(False)
        self.applyButton.setEnabled(False)
        self.resultEditor.setReadOnly(True)
        self.statusLabel.setText("ИИ обрабатывает заметку…")
        self.worker = AiWorker(
            profile, "process", self.promptInput.toPlainText(), self.text, self
        )
        self.worker.result.connect(self.showResult)
        self.worker.error.connect(self.statusLabel.setText)
        self.worker.finished.connect(self.finishRequest)
        self.worker.start()

    def showResult(self, text):
        self.resultReady = True
        self.resultEditor.setPlainText(text)
        self.textTabs.setCurrentIndex(0)
        self.applyButton.setVisible(True)
        self.runButton.setText("Попробовать ещё раз")
        self.statusLabel.setText(
            "Проверьте результат. Применение перенесёт его в редактор заметки."
        )

    def updateApplyButton(self):
        self.applyButton.setEnabled(
            self.worker is None and self.resultReady
            and bool(self.resultEditor.toPlainText().strip())
        )

    def finishRequest(self):
        self.worker.deleteLater()
        self.worker = None
        self.controls.setEnabled(True)
        self.cancelButton.setEnabled(True)
        self.resultEditor.setReadOnly(False)
        self.updateApplyButton()

    def applyResult(self):
        if (self.worker is None and self.resultReady
                and self.resultEditor.toPlainText().strip()):
            self.accept()

    def done(self, result):
        if self.worker is not None:
            self.statusLabel.setText("Дождитесь завершения запроса к ИИ.")
            return
        super().done(result)

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
            self.statusLabel.setText("Дождитесь завершения запроса к ИИ.")
        else:
            super().closeEvent(event)
