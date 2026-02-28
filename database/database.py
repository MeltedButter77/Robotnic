import sqlite3
from config.paths import DB_PATH


class Database:
    def __init__(self):
        self.connection = sqlite3.connect(DB_PATH)
        self.cursor = self.connection.cursor()
        self._ensure_tables()

    def _ensure_tables(self):
        tables = {
            "temp_channels": {
                "guild_id": "INTEGER",
                "channel_id": "INTEGER",
                "creator_id": "INTEGER",
                "owner_id": "INTEGER",
                "channel_state": "INTEGER",
                "number": "INTEGER",
                "is_renamed": "INTEGER",
            },
            "creator_channels": {
                "guild_id": "INTEGER",
                "channel_id": "INTEGER",
                "child_name": "TEXT",
                "user_limit": "INTEGER",
                "child_category_id": "INTEGER",
                "child_overwrites": "INTEGER",
                "default_role_id": "INTEGER",
            },
            "guild_settings": {
                "guild_id": "INTEGER",
                "logs_channel_id": "INTEGER",
                "profanity_filter": "TEXT",
                "mention_owner_bool": "INTEGER",
                "enabled_controls": "TEXT",
                "control_options": "TEXT",
                "enabled_log_events": "TEXT",
            },
        }

        for table_name, columns in tables.items():
            # Create table if it doesn't exist
            columns_sql = ", ".join(f"{col} {ctype}" for col, ctype in columns.items())
            self.cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_sql})"
            )

            # Get existing columns
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = {row[1] for row in self.cursor.fetchall()}

            # Add missing columns
            for column_name, column_type in columns.items():
                if column_name not in existing_columns:
                    self.cursor.execute(
                        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                    )

        self.connection.commit()

    def close(self):
        if self.connection:
            self.connection.close()
