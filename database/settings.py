import config


class Settings:
    def __init__(self, database):
        self.connection = database.connection

    def get_theme(self):
        row = self.connection.execute(
            "SELECT value FROM settings WHERE name = ?", ("theme",)
        ).fetchone()
        return row["value"] if row and row["value"] == "dark" else "light"

    def save_theme(self, theme):
        with self.connection:
            self.connection.execute(
                "INSERT OR REPLACE INTO settings VALUES (?, ?)",
                ("theme", theme),
            )

    def get_hotkey(self):
        row = self.connection.execute(
            "SELECT value FROM settings WHERE name = ?", ("hotkey",)
        ).fetchone()
        return row["value"] if row is not None else config.HOTKEY

    def get_font_size(self):
        row = self.connection.execute(
            "SELECT value FROM settings WHERE name = ?", ("font_size",)
        ).fetchone()
        try:
            size = (
                int(row["value"])
                if row is not None
                else config.NOTE_FONT_SIZE
            )
        except (TypeError, ValueError):
            return config.NOTE_FONT_SIZE
        if config.NOTE_FONT_MIN <= size <= config.NOTE_FONT_MAX:
            return size
        return config.NOTE_FONT_SIZE

    def save_font_size(self, size):
        if not config.NOTE_FONT_MIN <= size <= config.NOTE_FONT_MAX:
            raise ValueError("Недопустимый размер текста заметки")
        with self.connection:
            self.connection.execute(
                "INSERT OR REPLACE INTO settings VALUES (?, ?)",
                ("font_size", str(size)),
            )

    def save_hotkey(self, shortcut):
        with self.connection:
            self.connection.execute(
                "INSERT OR REPLACE INTO settings (name, value) VALUES (?, ?)",
                ("hotkey", shortcut),
            )
