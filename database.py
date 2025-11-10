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
            CREATE TABLE IF NOT EXISTS creator_channels (
                guild_id INTEGER,
                channel_id INTEGER,
                child_name TEXT,
                user_limit INTEGER,
                child_category_id INTEGER
            )
        """)
        self.connection.commit()

    def is_temp_channel(self, channel_id):
        """
        Returns if a channel id is in the temp_channels tabel.
        """
        self.cursor.execute(
            "SELECT 1 FROM temp_channels WHERE channel_id = ? LIMIT 1",
            (channel_id,)
        )
        return self.cursor.fetchone() is not None
    def remove_temp_channel(self, channel_id):
        """
        Remove a temporary channel record by its channel_id.
        """
        self.cursor.execute(
            "DELETE FROM temp_channels WHERE channel_id = ?",
            (channel_id,)
        )
        self.connection.commit()

    def add_temp_channel(self, guild_id, channel_id, creator_id, owner_id, channel_state, number, is_renamed):
        """
        Insert or replace a temporary channel record.
        """
        self.cursor.execute("""
                INSERT OR REPLACE INTO temp_channels 
                (guild_id, channel_id, creator_id, owner_id, channel_state, number, is_renamed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (guild_id, channel_id, creator_id, owner_id, channel_state, number, is_renamed))
        self.connection.commit()

    def get_temp_channel_ids(self):
        """
        Returns a list of all channel_id values from temp_channels.
        """
        self.cursor.execute("SELECT channel_id FROM temp_channels")
        rows = self.cursor.fetchall()
        return [row[0] for row in rows]

    def get_creator_channel_ids(self):
        """
        Returns a list of all channel_id values from creator_channels.
        """
        self.cursor.execute("SELECT channel_id FROM creator_channels")
        rows = self.cursor.fetchall()
        return [row[0] for row in rows]

    def close(self):
        if self.connection:
            self.connection.close()
