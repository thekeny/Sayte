import sqlite3
from uuid import uuid4

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox, QPushButton

import config
from ai.worker import AiWorker
from ui.ai_controls import fillModels, modelId, profileIcon


class ProviderWindow(QDialog):
    def __init__(self, providers, parent=None):
        super().__init__(parent)
        self.providers = providers
        self.profiles = providers.getProfiles()
        self.current = -1
        self.worker = None
        self.initUI()

    def initUI(self):
        uic.loadUi(config.PROVIDER_UI_PATH, self)
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
        self.profileCombo.currentIndexChanged.connect(self.changeProfile)
        self.addButton.clicked.connect(self.addProfile)
        self.deleteButton.clicked.connect(self.deleteProfile)
        self.refreshButton.clicked.connect(self.refreshModels)
        self.saveButton.clicked.connect(self.saveProfiles)
        self.cancelButton.clicked.connect(self.reject)
        self.reloadProfiles(self.providers.getActiveProfile())

    def storeFields(self):
        if self.current < 0:
            return
        self.profiles[self.current].update(
            {
                "name": self.nameInput.text().strip(),
                "url": self.urlInput.text().strip().rstrip("/"),
                "api_key": self.keyInput.text().strip(),
                "model": modelId(self.modelCombo),
            }
        )
        self.profileCombo.setItemText(
            self.current, self.profiles[self.current]["name"]
        )
        self.profileCombo.setItemIcon(
            self.current, profileIcon(self.profiles[self.current])
        )

    def reloadProfiles(self, selected):
        self.profileCombo.blockSignals(True)
        self.profileCombo.clear()
        for profile in self.profiles:
            self.profileCombo.addItem(
                profileIcon(profile), profile["name"], profile["id"]
            )
        index = self.profileCombo.findData(selected)
        if index < 0 and self.profiles:
            index = 0
        self.profileCombo.setCurrentIndex(index)
        self.profileCombo.blockSignals(False)
        self.current = -1
        self.changeProfile(index)

    def changeProfile(self, index):
        self.storeFields()
        self.current = index
        self.fields.setEnabled(index >= 0)
        self.deleteButton.setEnabled(index >= 0)
        if index < 0:
            self.nameInput.clear()
            self.urlInput.clear()
            self.keyInput.clear()
            self.modelCombo.clear()
            return
        profile = self.profiles[index]
        self.nameInput.setText(profile["name"])
        self.urlInput.setText(profile["url"])
        self.keyInput.setText(profile["api_key"])
        fillModels(self.modelCombo, [], profile["model"])
        self.statusLabel.clear()

    def addProfile(self):
        self.storeFields()
        profile = {
            "id": uuid4().hex,
            "name": "Новое подключение",
            "kind": "custom",
            "url": "",
            "api_key": "",
            "model": "",
        }
        self.profiles.append(profile)
        self.reloadProfiles(profile["id"])
        self.nameInput.setFocus()
        self.nameInput.selectAll()

    def deleteProfile(self):
        if self.current < 0:
            return
        answer = QMessageBox.question(
            self,
            "Подключения ИИ",
            "Удалить выбранное подключение?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.profiles.pop(self.current)
            self.reloadProfiles("")

    def refreshModels(self):
        if self.worker is not None or self.current < 0:
            return
        self.storeFields()
        profile = self.profiles[self.current]
        try:
            self.providers.validateProfile(profile)
        except ValueError as error:
            self.statusLabel.setText(str(error))
            return
        self.statusLabel.setText("Загрузка моделей…")
        self.setBusy(True)
        self.worker = AiWorker(profile, "models", parent=self)
        self.worker.result.connect(self.showModels)
        self.worker.error.connect(self.statusLabel.setText)
        self.worker.finished.connect(self.finishRequest)
        self.worker.start()

    def showModels(self, models):
        selected = modelId(self.modelCombo)
        fillModels(self.modelCombo, models, selected)
        self.statusLabel.setText(f"Моделей: {len(models)}")

    def setBusy(self, busy):
        for widget in (
            self.fields,
            self.profileCombo,
            self.addButton,
            self.saveButton,
            self.cancelButton,
            self.deleteButton,
        ):
            widget.setEnabled(not busy)

    def finishRequest(self):
        self.worker.deleteLater()
        self.worker = None
        self.setBusy(False)

    def saveProfiles(self):
        self.storeFields()
        try:
            self.providers.saveProfiles(
                self.profiles, self.profileCombo.currentData()
            )
        except (ValueError, sqlite3.Error) as error:
            QMessageBox.warning(self, "Подключения ИИ", str(error))
            return
        self.accept()

    def done(self, result):
        if self.worker is not None:
            self.statusLabel.setText("Дождитесь завершения загрузки моделей.")
            return
        super().done(result)

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
            self.statusLabel.setText("Дождитесь завершения загрузки моделей.")
        else:
            super().closeEvent(event)
