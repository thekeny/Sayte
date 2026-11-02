import sqlite3

from PyQt6 import uic
from PyQt6.QtGui import QIcon, QTextCursor
from PyQt6.QtWidgets import QDialog, QMessageBox, QPushButton
from sounddevice import PortAudioError

import config
from ai.presets import getBuiltinPresets
from ai.worker import AiWorker
from transcription.worker import TranscriptionWorker


class PreviewWindow(QDialog):
    def __init__(self, providers, presets, text, parent=None):
        super().__init__(parent)
        self.providers = providers
        self.presets = presets
        self.text = text
        self.worker = None
        self.voiceWorker = None
        self.recording = False
        self.window = parent.window if parent is not None else None
        self.resultReady = False
        self.initUI()

    def initUI(self):
        uic.loadUi(config.PREVIEW_UI_PATH, self)
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
        self.sourceEditor.setPlainText(self.text)
        self.applyButton.setVisible(False)
        self.promptVoiceButton.setIcon(QIcon(config.MICROPHONE_ICON_PATH))
        self.promptVoiceButton.clicked.connect(self.toggleRecording)
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
        self.promptVoiceButton.setVisible(preset is None)

    def toggleRecording(self):
        if self.worker is not None or self.voiceWorker is not None:
            return
        if self.recording:
            self.stopRecording()
            return
        if self.presetCombo.currentData() is not None:
            return
        if (self.window is None or self.window.state != "idle"
                or self.window.worker is not None):
            self.promptVoiceButton.setChecked(False)
            self.statusLabel.setText(config.PROMPT_VOICE_MESSAGES["busy"])
            return
        try:
            self.window.recorder.start()
        except (OSError, RuntimeError, ValueError, PortAudioError) as error:
            self.promptVoiceButton.setChecked(False)
            self.statusLabel.setText(
                config.PROMPT_VOICE_MESSAGES["start_error"].format(error=error)
            )
            return
        self.recording = True
        self.setVoiceBusy(True)
        self.promptVoiceButton.setChecked(True)
        self.promptVoiceButton.setText(config.PROMPT_VOICE_MESSAGES["stop"])
        self.statusLabel.setText(config.PROMPT_VOICE_MESSAGES["recording"])

    def setVoiceBusy(self, busy):
        self.presetCombo.setEnabled(not busy)
        self.runButton.setEnabled(not busy)
        self.cancelButton.setEnabled(not busy)
        if busy:
            self.applyButton.setEnabled(False)
        else:
            self.updateApplyButton()

    def stopRecording(self):
        self.recording = False
        self.promptVoiceButton.setChecked(False)
        try:
            audio = self.window.recorder.stop()
        except (OSError, RuntimeError, ValueError, PortAudioError) as error:
            self.statusLabel.setText(
                config.PROMPT_VOICE_MESSAGES["record_error"].format(error=error)
            )
            self.finishRecording()
            return
        if audio.size == 0:
            self.statusLabel.setText(config.PROMPT_VOICE_MESSAGES["empty"])
            self.finishRecording()
            return
        self.promptVoiceButton.setEnabled(False)
        self.statusLabel.setText(config.PROCESSING_TEXT)
        self.voiceWorker = TranscriptionWorker(self.window.whisper, audio, self)
        self.voiceWorker.status.connect(self.statusLabel.setText)
        self.voiceWorker.result.connect(self.appendPrompt)
        self.voiceWorker.error.connect(self.voiceError)
        self.voiceWorker.finished.connect(self.finishRecording)
        self.voiceWorker.start()

    def appendPrompt(self, text):
        text = text.strip()
        if not text:
            self.statusLabel.setText(config.PROMPT_VOICE_MESSAGES["empty"])
            return
        current = self.promptInput.toPlainText()
        separator = " " if current and not current[-1].isspace() else ""
        cursor = self.promptInput.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.beginEditBlock()
        cursor.insertText(separator + text)
        cursor.endEditBlock()
        self.promptInput.setTextCursor(cursor)
        self.promptInput.ensureCursorVisible()
        self.statusLabel.setText(config.PROMPT_VOICE_MESSAGES["ready"])

    def voiceError(self, message):
        self.statusLabel.setText(
            config.PROMPT_VOICE_MESSAGES["error"].format(error=message)
        )

    def finishRecording(self):
        if self.voiceWorker is not None:
            self.voiceWorker.deleteLater()
            self.voiceWorker = None
        self.promptVoiceButton.setEnabled(True)
        self.promptVoiceButton.setChecked(False)
        self.promptVoiceButton.setText(config.PROMPT_VOICE_MESSAGES["idle"])
        self.setVoiceBusy(False)

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
        if (self.worker is not None or self.recording
                or self.voiceWorker is not None):
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
        self.statusLabel.clear()

    def updateApplyButton(self):
        self.applyButton.setEnabled(
            self.worker is None and self.resultReady
            and not self.recording and self.voiceWorker is None
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
        if (self.worker is None and not self.recording
                and self.voiceWorker is None and self.resultReady
                and self.resultEditor.toPlainText().strip()):
            self.accept()

    def done(self, result):
        if self.recording or self.voiceWorker is not None:
            self.statusLabel.setText(config.PROMPT_VOICE_MESSAGES["wait"])
            return
        if self.worker is not None:
            self.statusLabel.setText("Дождитесь завершения запроса к ИИ.")
            return
        super().done(result)

    def closeEvent(self, event):
        if self.recording or self.voiceWorker is not None:
            event.ignore()
            self.statusLabel.setText(config.PROMPT_VOICE_MESSAGES["wait"])
        elif self.worker is not None:
            event.ignore()
            self.statusLabel.setText("Дождитесь завершения запроса к ИИ.")
        else:
            super().closeEvent(event)
