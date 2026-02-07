import json
import sqlite3
from config.paths import DB_PATH


class Database:
    def __init__(self):
        self.connection = sqlite3.connect(DB_PATH)
        self.cursor = self.connection.cursor()
        self._ensure_tables()

    def _ensure_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS temp_channels (
                guild_id INTEGER,
                channel_id INTEGER,
                creator_id INTEGER,
                owner_id INTEGER,
                channel_state INTEGER,
                number INTEGER,
                is_renamed INTEGER
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS creator_channels (
                guild_id INTEGER,
                channel_id INTEGER,
                child_name TEXT,
                user_limit INTEGER,
                child_category_id INTEGER,
                child_overwrites INTEGER
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS creator_channels (
                guild_id INTEGER,
                logs_channel_id INTEGER,
                profanity_filter_bool INTEGER,
                enabled_controls TEXT,
                mention_owner_bool INTEGER,
                logged_events TEXT
            )
        """)
        self.connection.commit()

    def close(self):
        if self.connection:
            self.connection.close()
