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
        self.shortcut = self.settings.getHotkey()
        self.recorder = Recorder()
        self.whisper = Whisper()
        self.session = RecordingSession(self.recorder, self.whisper, self)
        self.worker = None
        self.hotkey = None
        self.activeEditor = None
        self.state = "idle"
        self.pendingText = ""
        self.exitAfterSave = False
        self.initUI()
        self.loadNotes()

    def initUI(self):
        uic.loadUi(config.MAIN_UI_PATH, self)
        self.setWindowIcon(QIcon(config.ICON_PATH))
        self.settingsButton.setIcon(QIcon(config.SETTINGS_ICON_PATH))
        self.logoLabel.setPixmap(QPixmap(config.LOGO_PATH))
        self.recordButton.clicked.connect(self.toggleRecording)
        self.recordButton.installEventFilter(self)
        self.settingsButton.clicked.connect(self.openSettings)
        self.updateHotkeyHint()
        self.notesList.itemClicked.connect(self.showNote)
        self.searchInput.textChanged.connect(self.searchNotes)
        self.tagFilter.currentIndexChanged.connect(self.searchNotes)
        self.recordingWindow = RecordingWindow(self.recorder)
        self.recordingWindow.stopRequested.connect(self.toggleRecording)
        self.tray = Tray(self)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        else:
            self.statusLabel.setText("Системный трей недоступен")

    def eventFilter(self, watched, event):
        if (
            watched is self.recordButton
            and event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease)
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        ):
            return True
        return super().eventFilter(watched, event)

    def loadNotes(self, selectedId=None):
        selectedTag = self.tagFilter.currentData()
        self.tagFilter.blockSignals(True)
        self.tagFilter.clear()
        self.tagFilter.addItem("Все теги", None)
        for tag in self.tags.getTags():
            self.tagFilter.addItem(tag["name"], tag["id"])
        index = self.tagFilter.findData(selectedTag)
        self.tagFilter.setCurrentIndex(max(index, 0))
        self.tagFilter.blockSignals(False)
        selectedTag = self.tagFilter.currentData()
        rows = self.notes.getNotes()
        query = self.searchInput.text().strip().casefold()
        rows = [
            row
            for row in rows
            if query in row["title"].casefold()
            or query in row["current_text"].casefold()
        ]
        noteTags = {
            row["id"]: self.tags.getNoteTags(row["id"]) for row in rows
        }
        if selectedTag is not None:
            rows = [
                row
                for row in rows
                if any(tag["id"] == selectedTag for tag in noteTags[row["id"]])
            ]
        self.notesList.clear()
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
                if noteTags[row["id"]]
                else config.NOTE_HEIGHT
            )
            item.setSizeHint(QSize(0, height))
            self.notesList.addItem(item)
            card = uic.loadUi(config.NOTE_CARD_UI_PATH)
            card.titleLabel.setText(title)
            card.previewLabel.setText(preview)
            card.tagsLabel.setText(
                ", ".join(tag["name"] for tag in noteTags[row["id"]])
            )
            card.tagsLabel.setVisible(bool(noteTags[row["id"]]))
            card.pinLabel.setPixmap(
                QIcon(config.PINNED_ICON_PATH).pixmap(20, 20)
            )
            card.pinLabel.setVisible(bool(row["is_pinned"]))
            card.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.notesList.setItemWidget(item, card)
            if row["id"] == selectedId:
                selected = item
        if selected is not None:
            self.notesList.setCurrentItem(selected)
        elif rows:
            self.notesList.setCurrentRow(0)
        self.emptyLabel.setText(
            "Ничего не найдено."
            if query or selectedTag is not None
            else "Заметок пока нет. Начните запись."
        )
        self.emptyLabel.setVisible(not rows)

    def searchNotes(self):
        try:
            self.loadNotes()
        except sqlite3.Error as error:
            self.showError(f"Не удалось выполнить поиск: {error}")

    def showNote(self, current):
        try:
            note = self.notes.getNote(current.data(Qt.ItemDataRole.UserRole))
        except sqlite3.Error as error:
            self.showError(f"Не удалось открыть заметку: {error}")
            return
        if note is not None:
            try:
                dialog = NoteWindow(self.notes, note, self)
            except sqlite3.Error as error:
                self.showError(f"Не удалось загрузить теги: {error}")
                return
            self.activeEditor = dialog
            try:
                result = dialog.exec()
            finally:
                self.activeEditor = None
            if result == QDialog.DialogCode.Accepted:
                try:
                    self.loadNotes(note["id"])
                except sqlite3.Error as error:
                    self.showError(f"Не удалось обновить список: {error}")

    def openSettings(self):
        try:
            SettingsWindow(self).exec()
        except (OSError, sqlite3.Error) as error:
            self.showError(f"Не удалось открыть настройки: {error}")

    def updateHotkeyHint(self):
        self.statusLabel.setText(
            f"{self.shortcut.upper()} — начать или остановить запись"
        )

    def startHotkey(self):
        from utils.hotkey import Hotkey

        self.hotkey = Hotkey(self.shortcut)
        self.hotkey.activated.connect(
            self.toggleRecording, Qt.ConnectionType.QueuedConnection
        )
        self.hotkey.start()

    def applySettings(self, shortcut):
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
            self.startHotkey()
            self.settings.saveHotkey(shortcut)
        except (OSError, ImportError, ValueError, sqlite3.Error):
            if self.hotkey is not None:
                self.hotkey.stop()
            self.shortcut = previous
            try:
                self.startHotkey()
            except (OSError, ImportError, ValueError) as error:
                self.showError(
                    f"Не удалось восстановить горячую клавишу: {error}"
                )
            raise
        if self.state == "idle":
            self.updateHotkeyHint()
        elif self.state == "recording":
            self.setState(
                "recording", f"Запись… {self.shortcut.upper()} — остановить"
            )

    def setState(self, state, text):
        self.state = state
        self.statusLabel.setText(text)
        self.recordButton.setText(config.RECORD_BUTTON_TITLES[state])
        self.recordButton.setEnabled(state != "processing")
        self.tray.setState(state, text)
        self.recordingWindow.setState(state, text)

    def toggleRecording(self):
        if (
            self.activeEditor is not None
            and self.state == "idle"
            and self.worker is None
        ):
            self.activeEditor.toggleRecording()
            return
        if self.worker is not None or self.exitAfterSave:
            return
        if self.pendingText:
            self.saveNote()
            return

        if self.state == "recording":
            self.stopRecording()
            return
        try:
            self.session.startRecording(self)
        except (OSError, RuntimeError, ValueError, PortAudioError) as error:
            self.showError(f"Не удалось включить микрофон: {error}")
            return
        self.setState(
            "recording", f"Запись… {self.shortcut.upper()} — остановить"
        )

    def stopRecording(self):
        try:
            audio = self.session.stopRecording(self)
        except (OSError, RuntimeError, ValueError, PortAudioError) as error:
            self.exitAfterSave = False
            self.setState("idle", "Запись не удалась")
            self.showError(str(error))
            return
        if audio.size == 0:
            self.exitAfterSave = False
            self.setState("idle", "Запись пустая. Попробуйте ещё раз.")
            return

        self.setState("processing", config.PROCESSING_TEXT)
        self.worker = self.session.transcribe(
            self,
            audio,
            self.processText,
            self.transcriptionError,
            self.finishProcessing,
            self.processingStatus,
        )

    def processingStatus(self, text):
        self.setState("processing", text)

    def processText(self, text):
        if not text.strip():
            self.exitAfterSave = False
            self.setState("idle", "Речь не найдена. Попробуйте ещё раз.")
            return
        self.pendingText = text.strip()
        self.saveNote()

    def saveNote(self):
        try:
            noteId = self.notes.addNote(self.pendingText)
        except sqlite3.Error as error:
            self.exitAfterSave = False
            self.setState("saving", "Не удалось сохранить заметку")
            self.showError(
                f"{error}\nТекст остаётся в памяти. "
                "Нажмите «Повторить сохранение»."
            )
            return

        self.pendingText = ""
        self.setState("idle", "Запись сохранена")
        self.recordingWindow.hideTimer.start(config.SAVE_MESSAGE_MS)
        try:
            self.loadNotes(noteId)
        except sqlite3.Error as error:
            self.showError(f"Не удалось обновить список: {error}")

    def transcriptionError(self, message):
        self.exitAfterSave = False
        self.setState("idle", "Распознавание не удалось")
        self.showError(f"Не удалось распознать речь: {message}")

    def finishProcessing(self):
        self.worker = None
        if self.exitAfterSave:
            QTimer.singleShot(0, self.requestExit)

    def showError(self, message):
        self.showWindow()
        QMessageBox.warning(self, "Sayte", message)

    def showWindow(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def requestExit(self):
        if self.findChildren(AiWorker):
            QMessageBox.warning(
                self, "Выход из Sayte", "Дождитесь завершения запроса к ИИ."
            )
            return
        if self.activeEditor is not None:
            self.activeEditor.close()
            if self.activeEditor.isVisible():
                return
        if self.worker is not None or self.state == "recording":
            if self.exitAfterSave:
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
            self.exitAfterSave = True
            if self.state == "recording":
                self.stopRecording()
            elif self.worker is None:
                self.requestExit()
            return
        if self.pendingText:
            self.saveNote()
            if self.pendingText:
                return

        if self.hotkey is not None:
            self.hotkey.stop()
        self.recorder.close()
        self.database.close()
        self.tray.hide()
        self.recordingWindow.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        event.ignore()
        if self.tray.isVisible():
            self.hide()
        else:
            self.requestExit()
