import sqlite3
from pathlib import Path

import config


class Database:
    def __init__(self, path=config.DB_PATH):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        try:
            with self.connection:
                self.connection.execute("""
                    CREATE TABLE IF NOT EXISTS notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        original_text TEXT NOT NULL,
                        current_text TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                self.connection.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        name TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)
        except sqlite3.Error:
            self.connection.close()
            raise

    def close(self):
        self.connection.close()
