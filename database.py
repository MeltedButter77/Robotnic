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
                child_category_id INTEGER,
                child_overwrites INTEGER
            )
        """)
        self.connection.commit()

    def get_temp_channel_info(self, channel_id):
        self.cursor.execute("""
            SELECT guild_id, channel_id, creator_id, owner_id, channel_state, number, is_renamed
            FROM temp_channels
            WHERE channel_id = ?
        """, (channel_id,))
        row = self.cursor.fetchone()
        if row is None:
            return None

        class CreatorInfo:
            def __init__(self, guild_id, channel_id, creator_id, owner_id, channel_state, number, is_renamed):
                self.guild_id = guild_id
                self.channel_id = channel_id
                self.creator_id = creator_id
                self.owner_id = owner_id
                self.channel_state = channel_state
                self.number = number
                self.is_renamed = is_renamed
        return CreatorInfo(*row)

    def edit_creator_channel(
            self,
            channel_id: int,
            child_name: str = None,
            user_limit: int = None,
            child_category_id: int = None,
            child_overwrites: int = None
    ):
        """
        Update a creator channel's attributes in the database.
        Only updates provided arguments.
        """

        # Build dynamic SET clause based on provided arguments
        fields = []
        values = []

        if child_name is not None:
            fields.append("child_name = ?")
            values.append(child_name)

        if user_limit is not None:
            fields.append("user_limit = ?")
            values.append(user_limit)

        if child_category_id is not None:
            fields.append("child_category_id = ?")
            values.append(child_category_id)

        if child_overwrites is not None:
            fields.append("child_overwrites = ?")
            values.append(child_overwrites)

        if not fields:
            # Nothing to update
            return False

        # Add the WHERE clause value
        values.append(channel_id)

        query = f"""
            UPDATE creator_channels
            SET {', '.join(fields)}
            WHERE channel_id = ?
        """

        self.cursor.execute(query, tuple(values))
        self.connection.commit()

        return self.cursor.rowcount > 0  # Returns True if a row was updated

    def get_creator_channel_info(self, channel_id):
        self.cursor.execute("""
            SELECT guild_id, channel_id, child_name, user_limit, child_category_id, child_overwrites
            FROM creator_channels
            WHERE channel_id = ?
        """, (channel_id,))
        row = self.cursor.fetchone()
        if row is None:
            return None

        class CreatorInfo:
            def __init__(self, guild_id, channel_id, child_name, user_limit, child_category_id, child_overwrites):
                self.guild_id = guild_id
                self.channel_id = channel_id
                self.child_name = child_name
                self.user_limit = user_limit
                self.child_category_id = child_category_id
                self.child_overwrites = child_overwrites
        return CreatorInfo(*row)

    def add_creator_channel(self, guild_id, channel_id, child_name, user_limit, child_category_id, child_overwrites):
        """
        Insert or replace a creator channel record into creator_channels.
        """
        self.cursor.execute("""
            INSERT OR REPLACE INTO creator_channels
            (guild_id, channel_id, child_name, user_limit, child_category_id, child_overwrites)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (guild_id, channel_id, child_name, user_limit, child_category_id, child_overwrites))
        self.connection.commit()

    def remove_temp_channel(self, channel_id):
        """
        Remove a temporary channel record by its channel_id.
        """
        self.cursor.execute(
            "DELETE FROM temp_channels WHERE channel_id = ?",
            (channel_id,)
        )
        self.connection.commit()

    def remove_creator_channel(self, channel_id):
        """
        Remove a temporary channel record by its channel_id.
        """
        self.cursor.execute(
            "DELETE FROM creator_channels WHERE channel_id = ?",
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

    def get_creator_channel_ids(self, guild_id: int = None, child_category_id: int = None):
        """
        Returns a list of channel_id values from creator_channels.
        Optional filters:
            guild_id: only return channels in this guild
            child_category_id: only return channels in this category
        """
        query = "SELECT channel_id FROM creator_channels"
        params = []

        filters = []
        if guild_id is not None:
            filters.append("guild_id = ?")
            params.append(guild_id)
        if child_category_id is not None:
            filters.append("child_category_id = ?")
            params.append(child_category_id)

        if filters:
            query += " WHERE " + " AND ".join(filters)

        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        return [row[0] for row in rows]

    def close(self):
        if self.connection:
            self.connection.close()
