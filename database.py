import sqlite3
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, 'database.db')


class Database:
    def __init__(self, db_path=db_path):
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        self._ensure_tables()

    def _ensure_tables(self):
        # Example table
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
            CREATE TABLE IF NOT EXISTS temp_channel_hubs (
                guild_id INTEGER,
                channel_id INTEGER,
                child_name TEXT,
                user_limit INTEGER,
                child_category_id INTEGER
            )
        """)
        self.connection.commit()

    def close(self):
        if self.connection:
            self.connection.close()
