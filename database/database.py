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
                profanity_filter INTEGER,
                enabled_controls TEXT
            )
        """)
        self.connection.commit()

    def add_guild_settings(self, guild_id, default_enabled_controls=None):
        logs_channel_id = None
        enabled_controls_json = json.dumps(default_enabled_controls)
        self.cursor.execute("""
            INSERT OR REPLACE INTO guild_settings
            (guild_id, logs_channel_id, enabled_controls)
            VALUES (?, ?, ?)
        """, (guild_id, logs_channel_id, enabled_controls_json))
        self.connection.commit()

    def get_guild_profanity_filter(self, guild_id):
        self.cursor.execute("""
                            SELECT logs_channel_id
                            FROM guild_settings
                            WHERE guild_id = ?
                            """, (guild_id,))
        row = self.cursor.fetchone()

        if row is None:
            # Default settings
            return {
                "guild_id": guild_id,
                "profanity_filter": 1,
            }

        profanity_filter = bool(row[0])

        return {
            "guild_id": guild_id,
            "profanity_filter": profanity_filter,
        }

    def get_guild_logs_channel_id(self, guild_id):
        self.cursor.execute("""
                            SELECT logs_channel_id
                            FROM guild_settings
                            WHERE guild_id = ?
                            """, (guild_id,))
        row = self.cursor.fetchone()

        if row is None:
            # Default settings
            return {
                "guild_id": guild_id,
                "logs_channel_id": None,
            }

        logs_channel_id = row[0]

        return {
            "guild_id": guild_id,
            "logs_channel_id": logs_channel_id,
        }

    def get_guild_settings(self, guild_id):
        self.cursor.execute("""
                            SELECT logs_channel_id, enabled_controls
                            FROM guild_settings
                            WHERE guild_id = ?
                            """, (guild_id,))
        row = self.cursor.fetchone()

        if row is None:
            # Add server to db
            self.add_guild_settings(guild_id, ["rename", "limit", "clear", "ban", "give", "delete"])
            # return Default settings
            return {
                "guild_id": guild_id,
                "logs_channel_id": None,
                "enabled_controls": ["rename", "limit", "clear", "ban", "give", "delete"]
            }

        logs_channel_id, enabled_controls_json = row
        enabled_controls = json.loads(enabled_controls_json) if enabled_controls_json else {}

        return {
            "guild_id": guild_id,
            "logs_channel_id": logs_channel_id,
            "enabled_controls": enabled_controls
        }

    def edit_guild_settings(
            self,
            guild_id: int,
            logs_channel_id: int = None,
            enabled_controls: str = None,
    ):
        fields = []
        values = []

        if logs_channel_id is not None:
            fields.append("logs_channel_id = ?")
            values.append(logs_channel_id)
        if logs_channel_id == 0:  # Allows to clear the channel
            logs_channel_id = None

        if enabled_controls is not None:
            fields.append("enabled_controls = ?")
            values.append(json.dumps(enabled_controls))

        if not fields:
            # Nothing to update
            return False

        # Add the WHERE clause value
        values.append(guild_id)

        query = f"""
            UPDATE guild_settings
            SET {', '.join(fields)}
            WHERE guild_id = ?
        """

        self.cursor.execute(query, tuple(values))
        self.connection.commit()

        return self.cursor.rowcount > 0  # Returns True if a row was updated

    def set_owner_id(self, channel_id, owner_id):
        self.cursor.execute("""UPDATE temp_channels SET owner_id = ? WHERE channel_id = ?""", (owner_id, channel_id,))
        self.connection.commit()

    def set_temp_channel_is_renamed(self, channel_id, bool):
        if bool:
            is_renamed = 1
        else:
            is_renamed = 0
        self.cursor.execute("""UPDATE temp_channels SET is_renamed = ? WHERE channel_id = ?""", (is_renamed, channel_id,))
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

    def fix_temp_channel_numbers(self):
        """
        Ensures all temp channels for each creator have correct ascending numbering:
        - If a creator has only one temp channel → number becomes 1.
        - If multiple → sorted and renumbered as 1..N.
        """

        # Fetch all temp channels
        self.cursor.execute("""
                            SELECT channel_id, creator_id, number
                            FROM temp_channels
                            """)
        rows = self.cursor.fetchall()

        if not rows:
            return

        # Group channels by creator
        creators = {}  # creator_id -> list of (channel_id, number)
        for channel_id, creator_id, number in rows:
            creators.setdefault(creator_id, []).append((channel_id, number))

        for creator_id, channels in creators.items():

            # Fetch creator channel info
            creator_info = self.get_creator_channel_info(creator_id)
            if creator_info is None:
                # Creator definition missing — cannot process
                continue

            # Skip creators whose child_name does not use {count}
            if "{count}" not in str(creator_info.child_name):
                continue

            # case 1; one temp channel
            if len(channels) == 1:
                channel_id, old_num = channels[0]
                if old_num != 1:  # Only update if incorrect
                    self.cursor.execute("""
                                        UPDATE temp_channels
                                        SET number = 1
                                        WHERE channel_id = ?
                                        """, (channel_id,))
                continue

            # case 2; multiple channels
            # Sort by current number
            channels_sorted = sorted(channels, key=lambda x: x[1])

            # Expected perfect sequence
            expected_numbers = list(range(1, len(channels_sorted) + 1))
            current_numbers = [num for _, num in channels_sorted]

            # Skip if already perfect
            if current_numbers == expected_numbers:
                continue

            # Renumber all channels
            for (channel_id, _old_num), new_num in zip(channels_sorted, expected_numbers):
                self.cursor.execute("""
                                    UPDATE temp_channels
                                    SET number = ?
                                    WHERE channel_id = ?
                                    """, (new_num, channel_id))

            # Save all updates
            self.connection.commit()

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

    def get_temp_channel_counts(self, creator_id):
        """
        Returns a list of all number values from all temp channels of a creator.
        """
        self.cursor.execute(
            "SELECT number FROM temp_channels WHERE creator_id = ?",
            (creator_id,)
        )
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
