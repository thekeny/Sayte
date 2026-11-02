import re
import sqlite3
from pathlib import Path

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon, QTextCursor
from PyQt6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QMessageBox
from PyQt6.QtWidgets import QLabel, QPushButton, QTextEdit, QVBoxLayout
from sounddevice import PortAudioError

import config
from transcription.worker import TranscriptionWorker


class NoteWindow(QDialog):
    def __init__(self, notes, note, parent=None):
        super().__init__(parent)
        self.notes = notes
        self.noteId = note["id"]
        self.originalText = note["current_text"]
        self.window = parent
        self.recording = False
        self.worker = None
        self.setWindowTitle(note["title"])
        self.resize(550, 500)
        layout = QVBoxLayout(self)
        self.editor = QTextEdit(self)
        self.editor.setAcceptRichText(False)
        self.editor.setPlainText(note["current_text"])
        layout.addWidget(self.editor)
        self.voiceStatus = QLabel(self)
        self.voiceStatus.setWordWrap(True)
        layout.addWidget(self.voiceStatus)
        buttons = QHBoxLayout()
        self.voiceButton = QPushButton(self)
        self.voiceButton.setFixedSize(36, 36)
        self.voiceButton.setIcon(
            QIcon(str(config.BASE_DIR / "images" / "microphone.svg"))
        )
        self.voiceButton.setIconSize(QSize(22, 22))
        self.voiceButton.setToolTip("Досказать заметку")
        self.voiceButton.setAccessibleName("Досказать заметку")
        self.voiceButton.setCheckable(True)
        self.voiceButton.clicked.connect(self.toggleRecording)
        buttons.addWidget(self.voiceButton)
        self.exportButton = QPushButton("Экспорт в TXT", self)
        self.saveButton = QPushButton("Сохранить", self)
        self.cancelButton = QPushButton("Отмена", self)
        buttons.addWidget(self.exportButton)
        buttons.addStretch()
        buttons.addWidget(self.saveButton)
        buttons.addWidget(self.cancelButton)
        layout.addLayout(buttons)
        self.exportButton.clicked.connect(self.exportText)
        self.saveButton.clicked.connect(self.saveChanges)
        self.cancelButton.clicked.connect(self.reject)

    def reject(self):
        if self.recording or self.worker is not None:
            QMessageBox.warning(
                self, "Голосовая запись",
                "Остановите запись и дождитесь распознавания перед закрытием."
            )
            return
        if self.editor.toPlainText() != self.originalText:
            message = QMessageBox(self)
            message.setWindowTitle("Несохранённые изменения")
            message.setText("В заметке есть несохранённые изменения.")
            message.setInformativeText("Сохранить изменения перед закрытием?")
            message.setIcon(QMessageBox.Icon.Warning)
            saveButton = message.addButton(
                "Сохранить", QMessageBox.ButtonRole.AcceptRole
            )
            discardButton = message.addButton(
                "Не сохранять", QMessageBox.ButtonRole.DestructiveRole
            )
            message.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
            message.setDefaultButton(saveButton)
            message.exec()
            if message.clickedButton() == saveButton:
                self.saveChanges()
                return
            if message.clickedButton() != discardButton:
                return
        super().reject()

    def saveChanges(self):
        if self.recording or self.worker is not None:
            return
        try:
            self.notes.updateNote(self.noteId, self.editor.toPlainText())
        except (sqlite3.Error, ValueError) as error:
            QMessageBox.warning(self, "Сохранение", str(error))
            return
        self.accept()

    def toggleRecording(self):
        if self.worker is not None:
            return
        if self.recording:
            self.stopRecording()
            return
        if (self.window is None or self.window.state != "idle"
                or self.window.worker is not None):
            self.voiceButton.setChecked(False)
            self.voiceStatus.setText("Дождитесь завершения текущей записи.")
            return
        try:
            self.window.recorder.start()
        except (OSError, RuntimeError, ValueError, PortAudioError) as error:
            self.voiceButton.setChecked(False)
            self.voiceStatus.setText(f"Не удалось включить микрофон: {error}")
            return
        self.recording = True
        self.voiceButton.setChecked(True)
        self.voiceButton.setToolTip("Остановить запись")
        self.voiceStatus.setText("Идёт запись. Нажмите микрофон ещё раз.")
        self.saveButton.setEnabled(False)
        self.cancelButton.setEnabled(False)

    def stopRecording(self):
        self.recording = False
        try:
            audio = self.window.recorder.stop()
        except (OSError, RuntimeError, ValueError, PortAudioError) as error:
            self.voiceStatus.setText(f"Ошибка записи: {error}")
            self.finishRecording()
            return
        if audio.size == 0:
            self.voiceStatus.setText("Запись пустая. Попробуйте ещё раз.")
            self.finishRecording()
            return
        self.voiceButton.setEnabled(False)
        self.voiceButton.setChecked(False)
        self.voiceStatus.setText("Распознавание речи…")
        self.worker = TranscriptionWorker(self.window.whisper, audio, self)
        self.worker.result.connect(self.appendText)
        self.worker.error.connect(self.voiceError)
        self.worker.finished.connect(self.finishRecording)
        self.worker.start()

    def appendText(self, text):
        text = text.strip()
        if not text:
            self.voiceStatus.setText("Речь не найдена. Попробуйте ещё раз.")
            return
        currentText = self.editor.toPlainText()
        separator = ""
        if currentText and not currentText.endswith("\n"):
            separator = "\n"
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.beginEditBlock()
        cursor.insertText(separator + text)
        cursor.endEditBlock()
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        self.voiceStatus.setText(
            "Текст добавлен. Сохраните изменения заметки."
        )

    def voiceError(self, message):
        self.voiceStatus.setText(f"Не удалось распознать речь: {message}")

    def finishRecording(self):
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None
        self.voiceButton.setEnabled(True)
        self.voiceButton.setChecked(False)
        self.voiceButton.setToolTip("Досказать заметку")
        self.saveButton.setEnabled(True)
        self.cancelButton.setEnabled(True)

    def exportText(self):
        name = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", self.windowTitle())
        name = name.rstrip(". ")[:60] or "Заметка"
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт заметки", f"{name}.txt", "Текстовые файлы (*.txt)"
        )
        if not path:
            return
        if not Path(path).suffix:
            path += ".txt"
        try:
            Path(path).write_text(self.editor.toPlainText(), encoding="utf-8")
        except OSError as error:
            QMessageBox.warning(self, "Экспорт", str(error))
