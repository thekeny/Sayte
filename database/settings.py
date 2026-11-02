import config


class Settings:
    def __init__(self, database):
        self.connection = database.connection

    def getHotkey(self):
        row = self.connection.execute(
            "SELECT value FROM settings WHERE name = ?", ("hotkey",)
        ).fetchone()
        return row["value"] if row is not None else config.HOTKEY

    def saveHotkey(self, shortcut):
        with self.connection:
            self.connection.execute(
                "INSERT OR REPLACE INTO settings (name, value) VALUES (?, ?)",
                ("hotkey", shortcut)
            )
