import os
import sqlite3

import config


class Database:
    def __init__(self, path=config.DB_PATH):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
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
                    CREATE TABLE IF NOT EXISTS tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE
                    )
                """)
                self.connection.execute("""
                    CREATE TABLE IF NOT EXISTS note_tags (
                        note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
                        tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                        PRIMARY KEY (note_id, tag_id)
                    )
                """)
                self.connection.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        name TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)
                self.connection.execute("""
                    CREATE TABLE IF NOT EXISTS ai_profiles (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        url TEXT NOT NULL,
                        api_key TEXT NOT NULL,
                        model TEXT NOT NULL
                    )
                """)
                self.connection.execute("""
                    CREATE TABLE IF NOT EXISTS ai_presets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        prompt TEXT NOT NULL
                    )
                """)
                columns = self.connection.execute(
                    "PRAGMA table_info(notes)"
                ).fetchall()
                if "is_pinned" not in [column["name"] for column in columns]:
                    self.connection.execute(
                        "ALTER TABLE notes ADD COLUMN is_pinned "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
                initialized = self.connection.execute(
                    "SELECT value FROM settings WHERE name = ?",
                    ("ai_initialized",)
                ).fetchone()
                if initialized is None:
                    self.connection.execute(
                        "INSERT INTO ai_profiles VALUES (?, ?, ?, ?, ?, ?)",
                        ("openrouter", "OpenRouter", "openrouter",
                         config.OPENROUTER_URL, "", "")
                    )
                    self.connection.executemany(
                        "INSERT INTO settings (name, value) VALUES (?, ?)",
                        [("ai_initialized", "1"),
                         ("ai_active_profile", "openrouter")]
                    )
        except sqlite3.Error:
            self.connection.close()
            raise

    def close(self):
        self.connection.close()
