import sqlite3

from PyQt6 import uic
from PyQt6.QtCore import QEvent, Qt, QTimer, QSize
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QDialog, QListWidgetItem, QMessageBox
from PyQt6.QtWidgets import QSystemTrayIcon, QWidget
from sounddevice import PortAudioError

import config
from ai.worker import AiWorker
from audio.recorder import Recorder
from database.database import Database
from database.notes import Notes
from database.presets import Presets
from database.providers import Providers
from database.settings import Settings
from database.tags import Tags
from transcription.whisper import Whisper
from audio.session import RecordingSession
from ui.recording_window import RecordingWindow
from ui.note_window import NoteWindow
from ui.settings_window import SettingsWindow
from ui.tray import Tray


class Sayte(QWidget):
    def __init__(self):
        super().__init__()
        self.database = Database()
        self.notes = Notes(self.database)
        self.tags = Tags(self.database)
        self.settings = Settings(self.database)
        self.providers = Providers(self.database)
        self.presets = Presets(self.database)
        self.shortcut = self.settings.get_hotkey()
        self.recorder = Recorder()
        self.whisper = Whisper()
        self.session = RecordingSession(self.recorder, self.whisper, self)
        self.worker = None
        self.hotkey = None
        self.active_editor = None
        self.state = "idle"
        self.pending_text = ""
        self.exit_after_save = False
        self.init_ui()
        self.load_notes()

    def init_ui(self):
        uic.loadUi(config.MAIN_UI_PATH, self)
        self.setWindowIcon(QIcon(config.ICON_PATH))
        self.settings_button.setIcon(QIcon(config.SETTINGS_ICON_PATH))
        self.logo_label.setPixmap(QPixmap(config.LOGO_PATH))
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.installEventFilter(self)
        self.settings_button.clicked.connect(self.open_settings)
        self.update_hotkey_hint()
        self.notes_list.itemClicked.connect(self.show_note)
        self.search_input.textChanged.connect(self.search_notes)
        self.tag_filter.currentIndexChanged.connect(self.search_notes)
        self.recording_window = RecordingWindow(self.recorder)
        self.recording_window.stop_requested.connect(self.toggle_recording)
        self.tray = Tray(self)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        else:
            self.status_label.setText("Системный трей недоступен")

    def eventFilter(self, watched, event):
        if (
            watched is self.record_button
            and event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease)
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        ):
            return True
        return super().eventFilter(watched, event)

    def load_notes(self, selected_id=None):
        selected_tag = self.tag_filter.currentData()
        self.tag_filter.blockSignals(True)
        self.tag_filter.clear()
        self.tag_filter.addItem("Все теги", None)
        for tag in self.tags.get_tags():
            self.tag_filter.addItem(tag["name"], tag["id"])
        index = self.tag_filter.findData(selected_tag)
        self.tag_filter.setCurrentIndex(max(index, 0))
        self.tag_filter.blockSignals(False)
        selected_tag = self.tag_filter.currentData()
        rows = self.notes.get_notes()
        query = self.search_input.text().strip().casefold()
        rows = [
            row
            for row in rows
            if query in row["title"].casefold()
            or query in row["current_text"].casefold()
        ]
        note_tags = {
            row["id"]: self.tags.get_note_tags(row["id"]) for row in rows
        }
        if selected_tag is not None:
            rows = [
                row
                for row in rows
                if any(
                    tag["id"] == selected_tag for tag in note_tags[row["id"]]
                )
            ]
        self.notes_list.clear()
        selected = None
        for row in rows:
            title = row["title"]
            preview = row["current_text"].splitlines()[0][
                : config.PREVIEW_LENGTH
            ]
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            height = (
                config.TAGGED_NOTE_HEIGHT
                if note_tags[row["id"]]
                else config.NOTE_HEIGHT
            )
            item.setSizeHint(QSize(0, height))
            self.notes_list.addItem(item)
            card = uic.loadUi(config.NOTE_CARD_UI_PATH)
            card.title_label.setText(title)
            card.preview_label.setText(preview)
            card.tags_label.setText(
                ", ".join(tag["name"] for tag in note_tags[row["id"]])
            )
            card.tags_label.setVisible(bool(note_tags[row["id"]]))
            card.pin_label.setPixmap(
                QIcon(config.PINNED_ICON_PATH).pixmap(20, 20)
            )
            card.pin_label.setVisible(bool(row["is_pinned"]))
            card.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.notes_list.setItemWidget(item, card)
            if row["id"] == selected_id:
                selected = item
        if selected is not None:
            self.notes_list.setCurrentItem(selected)
        elif rows:
            self.notes_list.setCurrentRow(0)
        self.empty_label.setText(
            "Ничего не найдено."
            if query or selected_tag is not None
            else "Заметок пока нет. Начните запись."
        )
        self.empty_label.setVisible(not rows)

    def search_notes(self):
        try:
            self.load_notes()
        except sqlite3.Error as error:
            self.show_error(f"Не удалось выполнить поиск: {error}")

    def show_note(self, current):
        try:
            note = self.notes.get_note(current.data(Qt.ItemDataRole.UserRole))
        except sqlite3.Error as error:
            self.show_error(f"Не удалось открыть заметку: {error}")
            return
        if note is not None:
            try:
                dialog = NoteWindow(self.notes, note, self)
            except sqlite3.Error as error:
                self.show_error(f"Не удалось загрузить теги: {error}")
                return
            self.active_editor = dialog
            try:
                result = dialog.exec()
            finally:
                self.active_editor = None
            if result == QDialog.DialogCode.Accepted:
                try:
                    self.load_notes(note["id"])
                except sqlite3.Error as error:
                    self.show_error(f"Не удалось обновить список: {error}")

    def open_settings(self):
        try:
            SettingsWindow(self).exec()
        except (OSError, sqlite3.Error) as error:
            self.show_error(f"Не удалось открыть настройки: {error}")

    def update_hotkey_hint(self):
        self.status_label.setText(
            f"{self.shortcut.upper()} — начать или остановить запись"
        )

    def start_hotkey(self):
        from utils.hotkey import Hotkey

        self.hotkey = Hotkey(self.shortcut)
        self.hotkey.activated.connect(
            self.toggle_recording, Qt.ConnectionType.QueuedConnection
        )
        self.hotkey.start()

    def apply_settings(self, shortcut):
        parts = shortcut.split("+")
        modifiers = parts[:-1]
        if (
            not modifiers
            or len(set(modifiers)) != len(modifiers)
            or any(
                key not in ("ctrl", "alt", "shift", "win") for key in modifiers
            )
            or len(parts[-1]) != 1
            or not parts[-1].isascii()
            or not parts[-1].isalnum()
        ):
            raise ValueError(
                "Используйте Ctrl, Alt, Shift или Win и букву A–Z / цифру 0–9."
            )
        previous = self.shortcut
        if self.hotkey is not None:
            self.hotkey.stop()
        self.shortcut = shortcut
        try:
            self.start_hotkey()
            self.settings.save_hotkey(shortcut)
        except (OSError, ImportError, ValueError, sqlite3.Error):
            if self.hotkey is not None:
                self.hotkey.stop()
            self.shortcut = previous
            try:
                self.start_hotkey()
            except (OSError, ImportError, ValueError) as error:
                self.show_error(
                    f"Не удалось восстановить горячую клавишу: {error}"
                )
            raise
        if self.state == "idle":
            self.update_hotkey_hint()
        elif self.state == "recording":
            self.set_state(
                "recording", f"Запись… {self.shortcut.upper()} — остановить"
            )

    def set_state(self, state, text):
        self.state = state
        self.status_label.setText(text)
        self.record_button.setText(config.RECORD_BUTTON_TITLES[state])
        self.record_button.setEnabled(state != "processing")
        self.tray.set_state(state, text)
        self.recording_window.set_state(state, text)

    def toggle_recording(self):
        if (
            self.active_editor is not None
            and self.state == "idle"
            and self.worker is None
        ):
            self.active_editor.toggle_recording()
            return
        if self.worker is not None or self.exit_after_save:
            return
        if self.pending_text:
            self.save_note()
            return

        if self.state == "recording":
            self.stop_recording()
            return
        try:
            self.session.start_recording(self)
        except (OSError, RuntimeError, ValueError, PortAudioError) as error:
            self.show_error(f"Не удалось включить микрофон: {error}")
            return
        self.set_state(
            "recording", f"Запись… {self.shortcut.upper()} — остановить"
        )

    def stop_recording(self):
        try:
            audio = self.session.stop_recording(self)
        except (OSError, RuntimeError, ValueError, PortAudioError) as error:
            self.exit_after_save = False
            self.set_state("idle", "Запись не удалась")
            self.show_error(str(error))
            return
        if audio.size == 0:
            self.exit_after_save = False
            self.set_state("idle", "Запись пустая. Попробуйте ещё раз.")
            return

        self.set_state("processing", config.PROCESSING_TEXT)
        self.worker = self.session.transcribe(
            self,
            audio,
            self.process_text,
            self.transcription_error,
            self.finish_processing,
            self.processing_status,
        )

    def processing_status(self, text):
        self.set_state("processing", text)

    def process_text(self, text):
        if not text.strip():
            self.exit_after_save = False
            self.set_state("idle", "Речь не найдена. Попробуйте ещё раз.")
            return
        self.pending_text = text.strip()
        self.save_note()

    def save_note(self):
        try:
            note_id = self.notes.add_note(self.pending_text)
        except sqlite3.Error as error:
            self.exit_after_save = False
            self.set_state("saving", "Не удалось сохранить заметку")
            self.show_error(
                f"{error}\nТекст остаётся в памяти. "
                "Нажмите «Повторить сохранение»."
            )
            return

        self.pending_text = ""
        self.set_state("idle", "Запись сохранена")
        self.recording_window.hide_timer.start(config.SAVE_MESSAGE_MS)
        try:
            self.load_notes(note_id)
        except sqlite3.Error as error:
            self.show_error(f"Не удалось обновить список: {error}")

    def transcription_error(self, message):
        self.exit_after_save = False
        self.set_state("idle", "Распознавание не удалось")
        self.show_error(f"Не удалось распознать речь: {message}")

    def finish_processing(self):
        self.worker = None
        if self.exit_after_save:
            QTimer.singleShot(0, self.request_exit)

    def show_error(self, message):
        self.show_window()
        QMessageBox.warning(self, "Sayte", message)

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def request_exit(self):
        if self.findChildren(AiWorker):
            QMessageBox.warning(
                self, "Выход из Sayte", "Дождитесь завершения запроса к ИИ."
            )
            return
        if self.active_editor is not None:
            self.active_editor.close()
            if self.active_editor.isVisible():
                return
        if self.worker is not None or self.state == "recording":
            if self.exit_after_save:
                return
            answer = QMessageBox.question(
                self,
                "Выход из Sayte",
                "Дождаться сохранения заметки и выйти?\n"
                "«Нет» — продолжить работу.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.exit_after_save = True
            if self.state == "recording":
                self.stop_recording()
            elif self.worker is None:
                self.request_exit()
            return
        if self.pending_text:
            self.save_note()
            if self.pending_text:
                return

        if self.hotkey is not None:
            self.hotkey.stop()
        self.recorder.close()
        self.database.close()
        self.tray.hide()
        self.recording_window.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        event.ignore()
        if self.tray.isVisible():
            self.hide()
        else:
            self.request_exit()
