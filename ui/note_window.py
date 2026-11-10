import os
import re
import sqlite3

from PyQt6 import uic
from PyQt6.QtGui import QIcon, QTextCursor
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox
from sounddevice import PortAudioError

import config
from ui.preview_window import PreviewWindow


class NoteWindow(QDialog):
    def __init__(self, notes, note, parent=None):
        super().__init__(parent)
        self.notes = notes
        self.note_id = note["id"]
        self.original_text = note["current_text"]
        self.original_pinned = bool(note["is_pinned"])
        self.tags = parent.tags
        self.original_tags = [
            tag["name"] for tag in self.tags.get_note_tags(self.note_id)
        ]
        self.current_tags = self.original_tags.copy()
        self.window = parent
        self.recording = False
        self.worker = None
        self.ai_dialog = None
        self.init_ui()
        self.setWindowTitle(note["title"])
        self.editor.setPlainText(self.original_text)

    def init_ui(self):
        uic.loadUi(config.NOTE_UI_PATH, self)
        self.editor_splitter.setStretchFactor(0, 1)
        self.editor_splitter.setStretchFactor(1, 0)
        font = self.editor.font()
        font.setPointSize(self.window.settings.get_font_size())
        self.editor.setFont(font)
        self.pin_button.setChecked(self.original_pinned)
        self.update_pin_button()
        self.pin_button.toggled.connect(self.update_pin_button)
        self.voice_button.setIcon(QIcon(config.MICROPHONE_ICON_PATH))
        self.delete_button.setIcon(QIcon(config.TRASH_ICON_PATH))
        self.ai_button.setIcon(QIcon(config.CPU_ICON_PATH))
        self.ai_button.clicked.connect(self.open_ai)
        self.tag_input.returnPressed.connect(self.add_tags)
        self.update_tag_chips()
        self.voice_button.clicked.connect(self.toggle_recording)
        self.delete_button.clicked.connect(self.delete_note)
        self.export_button.clicked.connect(self.export_text)
        self.save_button.clicked.connect(self.save_changes)
        self.cancel_button.clicked.connect(self.reject)

    def update_pin_button(self):
        pinned = self.pin_button.isChecked()
        title = "Открепить" if pinned else "Закрепить"
        path = config.PINNED_ICON_PATH if pinned else config.PIN_ICON_PATH
        self.pin_button.setIcon(QIcon(path))
        self.pin_button.setText(title)
        self.pin_button.setToolTip(title)
        self.pin_button.setAccessibleName(title)

    def tag_names(self):
        return list(
            dict.fromkeys(
                self.current_tags
                + [
                    name.strip()
                    for name in self.tag_input.text().split(",")
                    if name.strip()
                ]
            )
        )

    def add_tags(self):
        self.current_tags = self.tag_names()
        self.tag_input.clear()
        self.update_tag_chips()

    def remove_tag(self, name):
        self.current_tags.remove(name)
        self.update_tag_chips()

    def update_tag_chips(self):
        while self.tags_layout.count():
            self.tags_layout.takeAt(0).widget().deleteLater()
        for index, name in enumerate(self.current_tags):
            chip = uic.loadUi(config.TAG_CHIP_UI_PATH)
            chip.setText(f"{name}  ×")
            chip.setToolTip(f"Удалить тег «{name}»")
            chip.setAccessibleName(f"Удалить тег {name}")
            chip.clicked.connect(
                lambda checked, tag=name: self.remove_tag(tag)
            )
            self.tags_layout.addWidget(chip, index // 3, index % 3)

    def has_changes(self):
        return (
            self.editor.toPlainText() != self.original_text
            or set(self.tag_names()) != set(self.original_tags)
            or self.pin_button.isChecked() != self.original_pinned
        )

    def reject(self):
        if self.ai_dialog is not None:
            QMessageBox.warning(
                self, "Обработка ИИ", "Закройте окно обработки ИИ."
            )
            return
        if self.recording or self.worker is not None:
            QMessageBox.warning(
                self,
                "Голосовая запись",
                "Остановите запись и дождитесь распознавания перед закрытием.",
            )
            return
        if self.has_changes():
            message = QMessageBox(self)
            message.setWindowTitle("Несохранённые изменения")
            message.setText("В заметке есть несохранённые изменения.")
            message.setInformativeText("Сохранить изменения перед закрытием?")
            message.setIcon(QMessageBox.Icon.Warning)
            save_button = message.add_button(
                "Сохранить", QMessageBox.ButtonRole.AcceptRole
            )
            discard_button = message.add_button(
                "Не сохранять", QMessageBox.ButtonRole.DestructiveRole
            )
            message.add_button("Отмена", QMessageBox.ButtonRole.RejectRole)
            message.setDefaultButton(save_button)
            message.exec()
            if message.clickedButton() == save_button:
                self.save_changes()
                return
            if message.clickedButton() != discard_button:
                return
        super().reject()

    def save_changes(self):
        if self.recording or self.worker is not None:
            return
        try:
            self.notes.update_note(
                self.note_id,
                self.editor.toPlainText(),
                self.tags,
                self.tag_names(),
                self.pin_button.isChecked(),
            )
        except (sqlite3.Error, ValueError) as error:
            QMessageBox.warning(self, "Сохранение", str(error))
            return
        self.accept()

    def delete_note(self):
        if self.recording or self.worker is not None:
            return
        message = "Удалить заметку?"
        if self.has_changes():
            message += "\nНесохранённые изменения будут потеряны."
        answer = QMessageBox.question(
            self,
            "Удаление заметки",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.notes.delete_note(self.note_id)
        except sqlite3.Error as error:
            QMessageBox.warning(self, "Удаление заметки", str(error))
            return
        self.accept()

    def toggle_recording(self):
        if self.ai_dialog is not None:
            self.ai_dialog.toggle_recording()
            return
        if self.worker is not None:
            return
        if self.recording:
            self.stop_recording()
            return
        if (
            self.window is None
            or self.window.state != "idle"
            or self.window.worker is not None
        ):
            self.voice_button.setChecked(False)
            self.voice_status.setText("Дождитесь завершения текущей записи.")
            return
        try:
            self.window.session.start_recording(self)
        except (OSError, RuntimeError, ValueError, PortAudioError) as error:
            self.voice_button.setChecked(False)
            self.voice_status.setText(f"Не удалось включить микрофон: {error}")
            return
        self.recording = True
        self.voice_button.setChecked(True)
        self.voice_button.setToolTip("Остановить запись")
        self.voice_status.setText("Запись…")
        self.save_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.ai_button.setEnabled(False)

    def stop_recording(self):
        self.recording = False
        try:
            audio = self.window.session.stop_recording(self)
        except (OSError, RuntimeError, ValueError, PortAudioError) as error:
            self.voice_status.setText(f"Ошибка записи: {error}")
            self.finish_recording()
            return
        if audio.size == 0:
            self.voice_status.setText("Запись пустая. Попробуйте ещё раз.")
            self.finish_recording()
            return
        self.voice_button.setEnabled(False)
        self.voice_button.setChecked(False)
        self.voice_status.setText("Распознавание речи…")
        self.worker = self.window.session.transcribe(
            self,
            audio,
            self.append_text,
            self.voice_error,
            self.finish_recording,
            self.voice_status.setText,
        )

    def append_text(self, text):
        text = text.strip()
        if not text:
            self.voice_status.setText("Речь не найдена. Попробуйте ещё раз.")
            return
        current_text = self.editor.toPlainText()
        separator = ""
        if current_text and not current_text.endswith("\n"):
            separator = "\n"
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.beginEditBlock()
        cursor.insertText(separator + text)
        cursor.endEditBlock()
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        self.voice_status.clear()

    def voice_error(self, message):
        self.voice_status.setText(f"Не удалось распознать речь: {message}")

    def finish_recording(self):
        if self.worker is not None:
            self.worker = None
        self.voice_button.setEnabled(True)
        self.voice_button.setChecked(False)
        self.voice_button.setToolTip("Досказать заметку")
        self.save_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.ai_button.setEnabled(True)

    def open_ai(self):
        if (
            self.recording
            or self.worker is not None
            or self.ai_dialog is not None
        ):
            return
        if not self.editor.toPlainText().strip():
            QMessageBox.warning(self, "Обработка ИИ", "Текст заметки пуст.")
            return
        try:
            dialog = PreviewWindow(
                self.window.providers,
                self.window.presets,
                self.editor.toPlainText(),
                self,
            )
            self.ai_dialog = dialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                cursor = self.editor.textCursor()
                cursor.select(QTextCursor.SelectionType.Document)
                cursor.insertText(dialog.result_editor.toPlainText())
                self.editor.setTextCursor(cursor)
                self.voice_status.clear()
        except sqlite3.Error:
            QMessageBox.warning(
                self, "Обработка ИИ", "Ошибка чтения базы данных."
            )
        finally:
            self.ai_dialog = None

    def export_text(self):
        name = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", self.windowTitle())
        name = name.rstrip(". ")[: config.TITLE_LENGTH] or "Заметка"
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
