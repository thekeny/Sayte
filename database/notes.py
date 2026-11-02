from datetime import datetime

import config


class Notes:
    def __init__(self, database):
        self.connection = database.connection

    def addNote(self, text):
        text = text.strip()
        if not text:
            raise ValueError("Нельзя сохранить пустую заметку")

        title = text.splitlines()[0][:config.TITLE_LENGTH]
        date = datetime.now().isoformat(timespec="seconds")
        with self.connection:
            cursor = self.connection.execute(
                """INSERT INTO notes
                (title, original_text, current_text, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)""",
                (title, text, text, date, date)
            )
        return cursor.lastrowid

    def getNotes(self):
        return self.connection.execute(
            """SELECT id, title, current_text, created_at, is_pinned FROM notes
            ORDER BY is_pinned DESC, created_at DESC, id DESC"""
        ).fetchall()

    def setPinned(self, noteId, pinned):
        with self.connection:
            self.connection.execute(
                "UPDATE notes SET is_pinned = ? WHERE id = ?",
                (int(pinned), noteId)
            )

    def getNote(self, noteId):
        return self.connection.execute(
            "SELECT * FROM notes WHERE id = ?", (noteId,)
        ).fetchone()

    def deleteNote(self, noteId):
        with self.connection:
            self.connection.execute("DELETE FROM notes WHERE id = ?", (noteId,))

    def updateNote(self, noteId, text, tags=None, tagNames=None, pinned=None):
        text = text.strip()
        if not text:
            raise ValueError("Нельзя сохранить пустую заметку")
        date = datetime.now().isoformat(timespec="seconds")
        with self.connection:
            self.connection.execute(
                """UPDATE notes SET title = ?, current_text = ?, updated_at = ?
                WHERE id = ?""",
                (text.splitlines()[0][:config.TITLE_LENGTH], text, date, noteId)
            )
            if pinned is not None:
                self.connection.execute(
                    "UPDATE notes SET is_pinned = ? WHERE id = ?",
                    (int(pinned), noteId)
                )
            if tags is not None:
                tags.setNoteTags(noteId, tagNames)
