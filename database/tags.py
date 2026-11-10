class Tags:
    def __init__(self, database):
        self.connection = database.connection

    def get_tags(self):
        return self.connection.execute(
            """SELECT DISTINCT tags.id, tags.name FROM tags
            JOIN note_tags ON tags.id = note_tags.tag_id
            ORDER BY tags.name COLLATE NOCASE"""
        ).fetchall()

    def get_note_tags(self, note_id):
        return self.connection.execute(
            """SELECT tags.id, tags.name FROM tags
            JOIN note_tags ON tags.id = note_tags.tag_id
            WHERE note_tags.note_id = ? ORDER BY tags.name COLLATE NOCASE""",
            (note_id,),
        ).fetchall()

    def set_note_tags(self, note_id, names):
        self.connection.execute(
            "DELETE FROM note_tags WHERE note_id = ?", (note_id,)
        )
        for name in names:
            self.connection.execute(
                "INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,)
            )
            self.connection.execute(
                """INSERT INTO note_tags (note_id, tag_id)
                SELECT ?, id FROM tags WHERE name = ?""",
                (note_id, name),
            )
        self.connection.execute(
            "DELETE FROM tags WHERE id NOT IN (SELECT tag_id FROM note_tags)"
        )
