class Tags:
    def __init__(self, database):
        self.connection = database.connection

    def getTags(self):
        return self.connection.execute(
            """SELECT DISTINCT tags.id, tags.name FROM tags
            JOIN note_tags ON tags.id = note_tags.tag_id
            ORDER BY tags.name COLLATE NOCASE"""
        ).fetchall()

    def getNoteTags(self, noteId):
        return self.connection.execute(
            """SELECT tags.id, tags.name FROM tags
            JOIN note_tags ON tags.id = note_tags.tag_id
            WHERE note_tags.note_id = ? ORDER BY tags.name COLLATE NOCASE""",
            (noteId,)
        ).fetchall()

    def setNoteTags(self, noteId, names):
        self.connection.execute(
            "DELETE FROM note_tags WHERE note_id = ?", (noteId,)
        )
        for name in names:
            self.connection.execute(
                "INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,)
            )
            self.connection.execute(
                """INSERT INTO note_tags (note_id, tag_id)
                SELECT ?, id FROM tags WHERE name = ?""", (noteId, name)
            )
        self.connection.execute(
            "DELETE FROM tags WHERE id NOT IN (SELECT tag_id FROM note_tags)"
        )
