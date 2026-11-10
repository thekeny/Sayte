import sqlite3
from uuid import uuid4

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox, QPushButton

import config
from ai.worker import AiWorker
from ui.ai_controls import fill_models, model_id, profile_icon


class ProviderWindow(QDialog):
    def __init__(self, providers, parent=None):
        super().__init__(parent)
        self.providers = providers
        self.profiles = providers.get_profiles()
        self.current = -1
        self.worker = None
        self.init_ui()

    def init_ui(self):
        uic.loadUi(config.PROVIDER_UI_PATH, self)
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
        self.profile_combo.currentIndexChanged.connect(self.change_profile)
        self.add_button.clicked.connect(self.add_profile)
        self.delete_button.clicked.connect(self.delete_profile)
        self.refresh_button.clicked.connect(self.refresh_models)
        self.save_button.clicked.connect(self.save_profiles)
        self.cancel_button.clicked.connect(self.reject)
        self.reload_profiles(self.providers.get_active_profile())

    def store_fields(self):
        if self.current < 0:
            return
        self.profiles[self.current].update(
            {
                "name": self.name_input.text().strip(),
                "url": self.url_input.text().strip().rstrip("/"),
                "api_key": self.key_input.text().strip(),
                "model": model_id(self.model_combo),
            }
        )
        self.profile_combo.setItemText(
            self.current, self.profiles[self.current]["name"]
        )
        self.profile_combo.setItemIcon(
            self.current, profile_icon(self.profiles[self.current])
        )

    def reload_profiles(self, selected):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for profile in self.profiles:
            self.profile_combo.addItem(
                profile_icon(profile), profile["name"], profile["id"]
            )
        index = self.profile_combo.findData(selected)
        if index < 0 and self.profiles:
            index = 0
        self.profile_combo.setCurrentIndex(index)
        self.profile_combo.blockSignals(False)
        self.current = -1
        self.change_profile(index)

    def change_profile(self, index):
        self.store_fields()
        self.current = index
        self.fields.setEnabled(index >= 0)
        self.delete_button.setEnabled(index >= 0)
        if index < 0:
            self.name_input.clear()
            self.url_input.clear()
            self.key_input.clear()
            self.model_combo.clear()
            return
        profile = self.profiles[index]
        self.name_input.setText(profile["name"])
        self.url_input.setText(profile["url"])
        self.key_input.setText(profile["api_key"])
        fill_models(self.model_combo, [], profile["model"])
        self.status_label.clear()

    def add_profile(self):
        self.store_fields()
        profile = {
            "id": uuid4().hex,
            "name": "Новое подключение",
            "kind": "custom",
            "url": "",
            "api_key": "",
            "model": "",
        }
        self.profiles.append(profile)
        self.reload_profiles(profile["id"])
        self.name_input.setFocus()
        self.name_input.selectAll()

    def delete_profile(self):
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
            self.reload_profiles("")

    def refresh_models(self):
        if self.worker is not None or self.current < 0:
            return
        self.store_fields()
        profile = self.profiles[self.current]
        try:
            self.providers.validate_profile(profile)
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        self.status_label.setText("Загрузка моделей…")
        self.set_busy(True)
        self.worker = AiWorker(profile, "models", parent=self)
        self.worker.result.connect(self.show_models)
        self.worker.error.connect(self.status_label.setText)
        self.worker.finished.connect(self.finish_request)
        self.worker.start()

    def show_models(self, models):
        selected = model_id(self.model_combo)
        fill_models(self.model_combo, models, selected)
        self.status_label.setText(f"Моделей: {len(models)}")

    def set_busy(self, busy):
        for widget in (
            self.fields,
            self.profile_combo,
            self.add_button,
            self.save_button,
            self.cancel_button,
            self.delete_button,
        ):
            widget.setEnabled(not busy)

    def finish_request(self):
        self.worker.deleteLater()
        self.worker = None
        self.set_busy(False)

    def save_profiles(self):
        self.store_fields()
        try:
            self.providers.save_profiles(
                self.profiles, self.profile_combo.currentData()
            )
        except (ValueError, sqlite3.Error) as error:
            QMessageBox.warning(self, "Подключения ИИ", str(error))
            return
        self.accept()

    def done(self, result):
        if self.worker is not None:
            self.status_label.setText("Дождитесь завершения загрузки моделей.")
            return
        super().done(result)

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
            self.status_label.setText("Дождитесь завершения загрузки моделей.")
        else:
            super().closeEvent(event)
