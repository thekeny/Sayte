from datetime import datetime

import config


class Notes:
    def __init__(self, database):
        self.connection = database.connection

    def add_note(self, text):
        text = text.strip()
        if not text:
            raise ValueError("Нельзя сохранить пустую заметку")

        title = text.splitlines()[0][: config.TITLE_LENGTH]
        date = datetime.now().isoformat(timespec="seconds")
        with self.connection:
            cursor = self.connection.execute(
                """INSERT INTO notes
                (title, original_text, current_text, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)""",
                (title, text, text, date, date),
            )
        return cursor.lastrowid

    def get_notes(self):
        return self.connection.execute(
            """SELECT id, title, current_text, created_at, is_pinned FROM notes
            ORDER BY is_pinned DESC, created_at DESC, id DESC"""
        ).fetchall()

    def set_pinned(self, note_id, pinned):
        with self.connection:
            self.connection.execute(
                "UPDATE notes SET is_pinned = ? WHERE id = ?",
                (int(pinned), note_id),
            )

    def get_note(self, note_id):
        return self.connection.execute(
            "SELECT * FROM notes WHERE id = ?", (note_id,)
        ).fetchone()

    def delete_note(self, note_id):
        with self.connection:
            self.connection.execute(
                "DELETE FROM notes WHERE id = ?", (note_id,)
            )

    def update_note(
        self, note_id, text, tags=None, tag_names=None, pinned=None
    ):
        text = text.strip()
        if not text:
            raise ValueError("Нельзя сохранить пустую заметку")
        date = datetime.now().isoformat(timespec="seconds")
        with self.connection:
            self.connection.execute(
                """UPDATE notes SET title = ?, current_text = ?, updated_at = ?
                WHERE id = ?""",
                (
                    text.splitlines()[0][: config.TITLE_LENGTH],
                    text,
                    date,
                    note_id,
                ),
            )
            if pinned is not None:
                self.connection.execute(
                    "UPDATE notes SET is_pinned = ? WHERE id = ?",
                    (int(pinned), note_id),
                )
            if tags is not None:
                tags.set_note_tags(note_id, tag_names)
