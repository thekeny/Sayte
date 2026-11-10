import sqlite3

from PyQt6 import uic
from PyQt6.QtGui import QIcon, QTextCursor
from PyQt6.QtWidgets import QDialog, QPushButton
from sounddevice import PortAudioError

import config
from ai.presets import get_builtin_presets
from ai.worker import AiWorker


class PreviewWindow(QDialog):
    def __init__(self, providers, presets, text, parent=None):
        super().__init__(parent)
        self.providers = providers
        self.presets = presets
        self.text = text
        self.worker = None
        self.voice_worker = None
        self.recording = False
        self.window = parent.window if parent is not None else None
        self.result_ready = False
        self.init_ui()

    def init_ui(self):
        uic.loadUi(config.PREVIEW_UI_PATH, self)
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
        self.source_editor.setPlainText(self.text)
        self.apply_button.setVisible(False)
        self.prompt_voice_button.setIcon(QIcon(config.MICROPHONE_ICON_PATH))
        self.prompt_voice_button.clicked.connect(self.toggle_recording)
        self.preset_combo.currentIndexChanged.connect(self.change_preset)
        self.load_actions()
        self.run_button.clicked.connect(self.process_text)
        self.apply_button.clicked.connect(self.apply_result)
        self.cancel_button.clicked.connect(self.reject)
        self.result_editor.textChanged.connect(self.update_apply_button)

    def load_actions(self):
        for preset in get_builtin_presets() + self.presets.get_presets():
            self.preset_combo.addItem(preset["name"], preset)
        self.preset_combo.addItem("Свой запрос", None)
        self.change_preset()

    def change_preset(self):
        preset = self.preset_combo.currentData()
        self.prompt_input.setPlainText(preset["prompt"] if preset else "")
        self.prompt_input.setVisible(preset is None)
        self.prompt_voice_button.setVisible(preset is None)

    def toggle_recording(self):
        if self.worker is not None or self.voice_worker is not None:
            return
        if self.recording:
            self.stop_recording()
            return
        if self.preset_combo.currentData() is not None:
            return
        if (
            self.window is None
            or self.window.state != "idle"
            or self.window.worker is not None
        ):
            self.prompt_voice_button.setChecked(False)
            self.status_label.setText(config.PROMPT_VOICE_MESSAGES["busy"])
            return
        try:
            self.window.session.start_recording(self)
        except (OSError, RuntimeError, ValueError, PortAudioError) as error:
            self.prompt_voice_button.setChecked(False)
            self.status_label.setText(
                config.PROMPT_VOICE_MESSAGES["start_error"].format(error=error)
            )
            return
        self.recording = True
        self.set_voice_busy(True)
        self.prompt_voice_button.setChecked(True)
        self.prompt_voice_button.setText(config.PROMPT_VOICE_MESSAGES["stop"])
        self.status_label.setText(config.PROMPT_VOICE_MESSAGES["recording"])

    def set_voice_busy(self, busy):
        self.preset_combo.setEnabled(not busy)
        self.run_button.setEnabled(not busy)
        self.cancel_button.setEnabled(not busy)
        if busy:
            self.apply_button.setEnabled(False)
        else:
            self.update_apply_button()

    def stop_recording(self):
        self.recording = False
        self.prompt_voice_button.setChecked(False)
        try:
            audio = self.window.session.stop_recording(self)
        except (OSError, RuntimeError, ValueError, PortAudioError) as error:
            self.status_label.setText(
                config.PROMPT_VOICE_MESSAGES["record_error"].format(
                    error=error
                )
            )
            self.finish_recording()
            return
        if audio.size == 0:
            self.status_label.setText(config.PROMPT_VOICE_MESSAGES["empty"])
            self.finish_recording()
            return
        self.prompt_voice_button.setEnabled(False)
        self.status_label.setText(config.PROCESSING_TEXT)
        self.voice_worker = self.window.session.transcribe(
            self,
            audio,
            self.append_prompt,
            self.voice_error,
            self.finish_recording,
            self.status_label.setText,
        )

    def append_prompt(self, text):
        text = text.strip()
        if not text:
            self.status_label.setText(config.PROMPT_VOICE_MESSAGES["empty"])
            return
        current = self.prompt_input.toPlainText()
        separator = " " if current and not current[-1].isspace() else ""
        cursor = self.prompt_input.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.beginEditBlock()
        cursor.insertText(separator + text)
        cursor.endEditBlock()
        self.prompt_input.setTextCursor(cursor)
        self.prompt_input.ensureCursorVisible()
        self.status_label.setText(config.PROMPT_VOICE_MESSAGES["ready"])

    def voice_error(self, message):
        self.status_label.setText(
            config.PROMPT_VOICE_MESSAGES["error"].format(error=message)
        )

    def finish_recording(self):
        if self.voice_worker is not None:
            self.voice_worker = None
        self.prompt_voice_button.setEnabled(True)
        self.prompt_voice_button.setChecked(False)
        self.prompt_voice_button.setText(config.PROMPT_VOICE_MESSAGES["idle"])
        self.set_voice_busy(False)

    def current_profile(self):
        active_id = self.providers.get_active_profile()
        profiles = self.providers.get_profiles()
        profile = next(
            (row for row in profiles if row["id"] == active_id), None
        )
        if profile is None or not profile["model"]:
            raise ValueError(
                "Выберите подключение и модель в настройках → Подключения ИИ."
            )
        self.providers.validate_profile(profile)
        return profile

    def process_text(self):
        if (
            self.worker is not None
            or self.recording
            or self.voice_worker is not None
        ):
            return
        try:
            profile = self.current_profile()
            if (
                not profile["model"]
                or not self.prompt_input.toPlainText().strip()
            ):
                raise ValueError("Укажите модель и промпт.")
            if not self.text.strip():
                raise ValueError("Текст заметки пуст.")
            if profile["kind"] == "openrouter" and not profile["api_key"]:
                raise ValueError("Укажите API-ключ в подключениях.")
        except (sqlite3.Error, ValueError) as error:
            self.status_label.setText(str(error))
            return
        self.result_ready = False
        self.result_editor.clear()
        self.start_request(profile)

    def start_request(self, profile):
        self.controls.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.apply_button.setEnabled(False)
        self.result_editor.setReadOnly(True)
        self.status_label.setText("ИИ обрабатывает заметку…")
        self.worker = AiWorker(
            profile,
            "process",
            self.prompt_input.toPlainText(),
            self.text,
            self,
        )
        self.worker.result.connect(self.show_result)
        self.worker.error.connect(self.status_label.setText)
        self.worker.finished.connect(self.finish_request)
        self.worker.start()

    def show_result(self, text):
        self.result_ready = True
        self.result_editor.setPlainText(text)
        self.text_tabs.setCurrentIndex(0)
        self.apply_button.setVisible(True)
        self.run_button.setText("Попробовать ещё раз")
        self.status_label.clear()

    def update_apply_button(self):
        self.apply_button.setEnabled(
            self.worker is None
            and self.result_ready
            and not self.recording
            and self.voice_worker is None
            and bool(self.result_editor.toPlainText().strip())
        )

    def finish_request(self):
        self.worker.deleteLater()
        self.worker = None
        self.controls.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.result_editor.setReadOnly(False)
        self.update_apply_button()

    def apply_result(self):
        if (
            self.worker is None
            and not self.recording
            and self.voice_worker is None
            and self.result_ready
            and self.result_editor.toPlainText().strip()
        ):
            self.accept()

    def done(self, result):
        if self.recording or self.voice_worker is not None:
            self.status_label.setText(config.PROMPT_VOICE_MESSAGES["wait"])
            return
        if self.worker is not None:
            self.status_label.setText("Дождитесь завершения запроса к ИИ.")
            return
        super().done(result)

    def closeEvent(self, event):
        if self.recording or self.voice_worker is not None:
            event.ignore()
            self.status_label.setText(config.PROMPT_VOICE_MESSAGES["wait"])
        elif self.worker is not None:
            event.ignore()
            self.status_label.setText("Дождитесь завершения запроса к ИИ.")
        else:
            super().closeEvent(event)
