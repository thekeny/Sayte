from datetime import datetime


class Notes:
    def __init__(self, database):
        self.connection = database.connection

    def addNote(self, text):
        text = text.strip()
        if not text:
            raise ValueError("Нельзя сохранить пустую заметку")

        title = text.splitlines()[0][:60]
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
            """SELECT id, title, current_text, created_at FROM notes
            ORDER BY created_at DESC, id DESC"""
        ).fetchall()

    def getNote(self, noteId):
        return self.connection.execute(
            "SELECT * FROM notes WHERE id = ?", (noteId,)
        ).fetchone()
