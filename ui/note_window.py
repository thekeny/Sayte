import os
import re
import sqlite3

from PyQt6 import uic
from PyQt6.QtGui import QIcon, QTextCursor
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox
from sounddevice import PortAudioError

import config
from transcription.worker import TranscriptionWorker
from ui.preview_window import PreviewWindow


class NoteWindow(QDialog):
    def __init__(self, notes, note, parent=None):
        super().__init__(parent)
        self.notes = notes
        self.noteId = note["id"]
        self.originalText = note["current_text"]
        self.originalPinned = bool(note["is_pinned"])
        self.tags = parent.tags
        self.originalTags = [
            tag["name"] for tag in self.tags.getNoteTags(self.noteId)
        ]
        self.currentTags = self.originalTags.copy()
        self.window = parent
        self.recording = False
        self.worker = None
        self.aiDialog = None
        self.initUI()
        self.setWindowTitle(note["title"])
        self.editor.setPlainText(self.originalText)

    def initUI(self):
        uic.loadUi(config.NOTE_UI_PATH, self)
        self.pinButton.setChecked(self.originalPinned)
        self.updatePinButton()
        self.pinButton.toggled.connect(self.updatePinButton)
        self.voiceButton.setIcon(QIcon(config.MICROPHONE_ICON_PATH))
        self.deleteButton.setIcon(QIcon(config.TRASH_ICON_PATH))
        self.aiButton.setIcon(QIcon(config.CPU_ICON_PATH))
        self.aiButton.clicked.connect(self.openAi)
        self.tagInput.returnPressed.connect(self.addTags)
        self.updateTagChips()
        self.voiceButton.clicked.connect(self.toggleRecording)
        self.deleteButton.clicked.connect(self.deleteNote)
        self.exportButton.clicked.connect(self.exportText)
        self.saveButton.clicked.connect(self.saveChanges)
        self.cancelButton.clicked.connect(self.reject)

    def updatePinButton(self):
        pinned = self.pinButton.isChecked()
        title = "Открепить" if pinned else "Закрепить"
        path = config.PINNED_ICON_PATH if pinned else config.PIN_ICON_PATH
        self.pinButton.setIcon(QIcon(path))
        self.pinButton.setText(title)
        self.pinButton.setToolTip(title)
        self.pinButton.setAccessibleName(title)

    def tagNames(self):
        return list(dict.fromkeys(
            self.currentTags + [name.strip() for name in
                                self.tagInput.text().split(",") if name.strip()]
        ))

    def addTags(self):
        self.currentTags = self.tagNames()
        self.tagInput.clear()
        self.updateTagChips()

    def removeTag(self, name):
        self.currentTags.remove(name)
        self.updateTagChips()

    def updateTagChips(self):
        while self.tagsLayout.count():
            self.tagsLayout.takeAt(0).widget().deleteLater()
        for index, name in enumerate(self.currentTags):
            chip = uic.loadUi(config.TAG_CHIP_UI_PATH)
            chip.setText(f"{name}  ×")
            chip.setToolTip(f"Удалить тег «{name}»")
            chip.setAccessibleName(f"Удалить тег {name}")
            chip.clicked.connect(lambda checked, tag=name: self.removeTag(tag))
            self.tagsLayout.addWidget(chip, index // 3, index % 3)

    def hasChanges(self):
        return (self.editor.toPlainText() != self.originalText
                or set(self.tagNames()) != set(self.originalTags)
                or self.pinButton.isChecked() != self.originalPinned)

    def reject(self):
        if self.aiDialog is not None:
            QMessageBox.warning(
                self, "Обработка ИИ", "Закройте окно обработки ИИ."
            )
            return
        if self.recording or self.worker is not None:
            QMessageBox.warning(
                self, "Голосовая запись",
                "Остановите запись и дождитесь распознавания перед закрытием."
            )
            return
        if self.hasChanges():
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
            self.notes.updateNote(
                self.noteId, self.editor.toPlainText(), self.tags, self.tagNames(),
                self.pinButton.isChecked()
            )
        except (sqlite3.Error, ValueError) as error:
            QMessageBox.warning(self, "Сохранение", str(error))
            return
        self.accept()

    def deleteNote(self):
        if self.recording or self.worker is not None:
            return
        message = "Удалить заметку?"
        if self.hasChanges():
            message += "\nНесохранённые изменения будут потеряны."
        answer = QMessageBox.question(
            self, "Удаление заметки", message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.notes.deleteNote(self.noteId)
        except sqlite3.Error as error:
            QMessageBox.warning(self, "Удаление заметки", str(error))
            return
        self.accept()

    def toggleRecording(self):
        if self.aiDialog is not None:
            self.aiDialog.toggleRecording()
            return
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
        self.voiceStatus.setText("Запись…")
        self.saveButton.setEnabled(False)
        self.cancelButton.setEnabled(False)
        self.deleteButton.setEnabled(False)
        self.aiButton.setEnabled(False)

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
        self.voiceStatus.clear()

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
        self.deleteButton.setEnabled(True)
        self.aiButton.setEnabled(True)

    def openAi(self):
        if self.recording or self.worker is not None or self.aiDialog is not None:
            return
        if not self.editor.toPlainText().strip():
            QMessageBox.warning(self, "Обработка ИИ", "Текст заметки пуст.")
            return
        try:
            dialog = PreviewWindow(
                self.window.providers, self.window.presets,
                self.editor.toPlainText(), self
            )
            self.aiDialog = dialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                cursor = self.editor.textCursor()
                cursor.select(QTextCursor.SelectionType.Document)
                cursor.insertText(dialog.resultEditor.toPlainText())
                self.editor.setTextCursor(cursor)
                self.voiceStatus.clear()
        except sqlite3.Error:
            QMessageBox.warning(self, "Обработка ИИ", "Ошибка чтения базы данных.")
        finally:
            self.aiDialog = None

    def exportText(self):
        name = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", self.windowTitle())
        name = name.rstrip(". ")[:config.TITLE_LENGTH] or "Заметка"
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт заметки", f"{name}.txt", "Текстовые файлы (*.txt)"
        )
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += ".txt"
        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write(self.editor.toPlainText())
        except OSError as error:
            QMessageBox.warning(self, "Экспорт", str(error))
