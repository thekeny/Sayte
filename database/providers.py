from urllib.parse import urlsplit


class Providers:
    def __init__(self, database):
        self.connection = database.connection

    def get_profiles(self):
        return [
            dict(row)
            for row in self.connection.execute(
                "SELECT * FROM ai_profiles ORDER BY rowid"
            )
        ]

    def get_active_profile(self):
        row = self.connection.execute(
            "SELECT value FROM settings WHERE name = ?", ("ai_active_profile",)
        ).fetchone()
        return row["value"] if row else ""

    def validate_profile(self, profile):
        if not profile["name"].strip():
            raise ValueError("Укажите название подключения.")
        url = urlsplit(profile["url"])
        if (
            url.scheme not in ("http", "https")
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("Укажите базовый HTTP или HTTPS URL API.")
        try:
            url.port
        except ValueError:
            raise ValueError("Некорректный порт в URL API.") from None

    def save_profiles(self, profiles, active_id):
        for profile in profiles:
            self.validate_profile(profile)
        ids = [profile["id"] for profile in profiles]
        if active_id not in ids:
            active_id = ids[0] if ids else ""
        with self.connection:
            self.connection.execute("DELETE FROM ai_profiles")
            self.connection.executemany(
                "INSERT INTO ai_profiles VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        p["id"],
                        p["name"],
                        p["kind"],
                        p["url"],
                        p["api_key"],
                        p["model"],
                    )
                    for p in profiles
                ],
            )
            self.connection.execute(
                "INSERT OR REPLACE INTO settings (name, value) VALUES (?, ?)",
                ("ai_active_profile", active_id),
            )

    def select_profile(self, profile_id, model):
        with self.connection:
            self.connection.execute(
                "UPDATE ai_profiles SET model = ? WHERE id = ?",
                (model, profile_id),
            )
            self.connection.execute(
                "INSERT OR REPLACE INTO settings (name, value) VALUES (?, ?)",
                ("ai_active_profile", profile_id),
            )
