class Presets:
    def __init__(self, database):
        self.connection = database.connection

    def get_presets(self):
        return [
            dict(row)
            for row in self.connection.execute(
                "SELECT * FROM ai_presets ORDER BY id"
            )
        ]

    def save_preset(self, preset_id, name, prompt):
        name, prompt = name.strip(), prompt.strip()
        if not name or not prompt:
            raise ValueError("Укажите название режима и промпт.")
        with self.connection:
            if preset_id is None:
                cursor = self.connection.execute(
                    "INSERT INTO ai_presets (name, prompt) VALUES (?, ?)",
                    (name, prompt),
                )
                return cursor.lastrowid
            self.connection.execute(
                "UPDATE ai_presets SET name = ?, prompt = ? WHERE id = ?",
                (name, prompt, preset_id),
            )
        return preset_id

    def delete_preset(self, preset_id):
        with self.connection:
            self.connection.execute(
                "DELETE FROM ai_presets WHERE id = ?", (preset_id,)
            )
