import sqlite3
from typing import List


class Database:
    """A class to handle all database operations."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Connect to the SQLite database and ensure tables exist."""
        self.connection = sqlite3.connect(self.db_path)
        self._ensure_tables()

    def _ensure_tables(self):
        """Create necessary tables if they do not exist."""
        if self.connection is None:
            raise Exception("No database connection. Please connect to a database before ensuring tables.")

        with self.connection:
            cursor = self.connection.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS temp_channels (
                    guild_id INTEGER,
                    channel_id INTEGER,
                    creator_id INTEGER,
                    owner_id INTEGER,
                    channel_state INTEGER,
                    number INTEGER
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS temp_channel_hubs (
                    guild_id INTEGER,
                    channel_id INTEGER,
                    child_name TEXT,
                    user_limit INTEGER
                )
            """)

            # List of any new collumns since the first db was made
            table_definitions = {
                'temp_channels': {
                    'creator_id': ('INTEGER', 0),
                    'owner_id': ('INTEGER', 0),
                    'channel_state': ('INTEGER', 0),
                    'number': ('INTEGER', 1)
                },
                'temp_channel_hubs': {
                    'child_name': ('TEXT', "{user}'s Channel"),
                    'user_limit': ('INTEGER', 0)
                }
            }

            # Iterate through tables and ensure columns exist
            for table_name, expected_columns in table_definitions.items():
                # Fetch current columns for the table
                cursor.execute(f"PRAGMA table_info({table_name})")
                current_columns_info = cursor.fetchall()
                current_column_names = {col_info[1] for col_info in current_columns_info}

                # Add missing columns
                for column_name, (column_type, default_value) in expected_columns.items():
                    if column_name not in current_column_names:
                        print(f"Column {column_name} not found in {table_name}, adding it.")
                        cursor.execute(f"""
                            ALTER TABLE {table_name}
                            ADD COLUMN {column_name} {column_type} DEFAULT {default_value}
                        """)

                # Commit the changes
                self.connection.commit()

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()

    def get_channel_state_id(self, guild_id: int, channel_id: int) -> int:
        """Retrieve the channel state of a temporary channel."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('SELECT channel_state FROM temp_channels WHERE guild_id = ? AND channel_id = ?', (guild_id, channel_id))
            row = cursor.fetchone()
            return row[0] if row else None

    def update_channel_state(self, guild_id: int, channel_id: int, new_state: int):
        """Update the channel state of a temporary channel."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('UPDATE temp_channels SET channel_state = ? WHERE guild_id = ? AND channel_id = ?', (new_state, guild_id, channel_id))
            self.connection.commit()

    def get_temp_channel_hubs(self, guild_id: int) -> List[int]:
        """Retrieve all temporary channel hub IDs for a guild."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('SELECT channel_id FROM temp_channel_hubs WHERE guild_id = ?', (guild_id,))
            return [row[0] for row in cursor.fetchall()]

    def get_child_name(self, channel_hub_id: int) -> str:
        """Retrieve the child name of a temporary channel hub."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('SELECT child_name FROM temp_channel_hubs WHERE channel_id = ?', (channel_hub_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def get_user_limit(self, channel_hub_id: int) -> str:
        """Retrieve the child name of a temporary channel hub."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('SELECT user_limit FROM temp_channel_hubs WHERE channel_id = ?', (channel_hub_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def add_temp_channel_hub(self, guild_id: int, channel_id: int, child_name: int, user_limit: int):
        """Add a new temporary channel hub to the database."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                'INSERT INTO temp_channel_hubs (guild_id, channel_id, child_name, user_limit) VALUES (?, ?, ?, ?)',
                (guild_id, channel_id, child_name, user_limit)
            )

    def delete_temp_channel_hub(self, guild_id: int, channel_id: int):
        """Delete a temporary channel hub from the database."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                'DELETE FROM temp_channel_hubs WHERE guild_id = ? AND channel_id = ?',
                (guild_id, channel_id)
            )

    def get_temp_channel_numbers(self, guild_id: int, creator_channel_id: int) -> List[int]:
        """Get all temporary channel numbers for a guild and creator."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                'SELECT number FROM temp_channels WHERE guild_id = ? AND creator_id = ?',
                (guild_id, creator_channel_id)
            )
            return [row[0] for row in cursor.fetchall()]

    def add_temp_channel(self, guild_id: int, channel_id: int, creator_channel_id: int, owner_id: int, number: int):
        """Add a new temporary channel to the database."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                'INSERT INTO temp_channels (guild_id, channel_id, creator_id, owner_id, channel_state, number) VALUES (?, ?, ?, ?, ?, ?)',
                (guild_id, channel_id, creator_channel_id, owner_id, 0, number)
            )

    def delete_temp_channel(self, channel_id: int):
        """Delete a temporary channel from the database."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('DELETE FROM temp_channels WHERE channel_id = ?', (channel_id,))

    def is_temp_channel(self, channel_id: int) -> bool:
        """Check if a channel is a temporary channel."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('SELECT 1 FROM temp_channels WHERE channel_id = ?', (channel_id,))
            return cursor.fetchone() is not None

    def get_owner_id(self, temp_channel_id: int) -> int:
        """Get the owner ID of a temporary channel."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('SELECT owner_id FROM temp_channels WHERE channel_id = ?', (temp_channel_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def set_owner_id(self, temp_channel_id: int, owner_id: int) -> int:
        """Set the owner ID of a temporary channel."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('UPDATE temp_channels SET owner_id = ? WHERE channel_id = ?', (owner_id, temp_channel_id,))
            self.connection.commit()
