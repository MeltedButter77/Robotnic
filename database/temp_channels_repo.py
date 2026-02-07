
class TempChannelsRepository:
    def __init__(self, db, repos):
        self.db = db
        self.repos = repos

    def set_owner_id(self, channel_id, owner_id):
        self.db.cursor.execute("""UPDATE temp_channels SET owner_id = ? WHERE channel_id = ?""", (owner_id, channel_id,))
        self.db.connection.commit()

    def set_temp_channel_is_renamed(self, channel_id, bool):
        if bool:
            is_renamed = 1
        else:
            is_renamed = 0
        self.db.cursor.execute("""UPDATE temp_channels SET is_renamed = ? WHERE channel_id = ?""", (is_renamed, channel_id,))
        self.db.connection.commit()

    def get_temp_channel_info(self, channel_id):
        self.db.cursor.execute("""
            SELECT guild_id, channel_id, creator_id, owner_id, channel_state, number, is_renamed
            FROM temp_channels
            WHERE channel_id = ?
        """, (channel_id,))
        row = self.db.cursor.fetchone()
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

    def fix_temp_channel_numbers(self):
        """
        Ensures all temp channels for each creator have correct ascending numbering:
        - If a creator has only one temp channel → number becomes 1.
        - If multiple → sorted and renumbered as 1..N.
        """

        # Fetch all temp channels
        self.db.cursor.execute("""
                            SELECT channel_id, creator_id, number
                            FROM temp_channels
                            """)
        rows = self.db.cursor.fetchall()

        if not rows:
            return

        # Group channels by creator
        creators = {}  # creator_id -> list of (channel_id, number)
        for channel_id, creator_id, number in rows:
            creators.setdefault(creator_id, []).append((channel_id, number))

        for creator_id, channels in creators.items():

            # Fetch creator channel info
            creator_info = self.repos.creator_channels.get_creator_channel_info(creator_id)
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
                    self.db.cursor.execute("""
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
                self.db.cursor.execute("""
                                    UPDATE temp_channels
                                    SET number = ?
                                    WHERE channel_id = ?
                                    """, (new_num, channel_id))

            # Save all updates
            self.db.connection.commit()

    def remove_temp_channel(self, channel_id):
        """
        Remove a temporary channel record by its channel_id.
        """
        self.db.cursor.execute(
            "DELETE FROM temp_channels WHERE channel_id = ?",
            (channel_id,)
        )
        self.db.connection.commit()

    def add_temp_channel(self, guild_id, channel_id, creator_id, owner_id, channel_state, number, is_renamed):
        """
        Insert or replace a temporary channel record.
        """
        self.db.cursor.execute("""
                INSERT OR REPLACE INTO temp_channels 
                (guild_id, channel_id, creator_id, owner_id, channel_state, number, is_renamed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (guild_id, channel_id, creator_id, owner_id, channel_state, number, is_renamed))
        self.db.connection.commit()

    def get_temp_channel_ids(self):
        """
        Returns a list of all channel_id values from temp_channels.
        """
        self.db.cursor.execute("SELECT channel_id FROM temp_channels")
        rows = self.db.cursor.fetchall()
        return [row[0] for row in rows]

    def get_temp_channel_counts(self, creator_id):
        """
        Returns a list of all number values from all temp channels of a creator.
        """
        self.db.cursor.execute(
            "SELECT number FROM temp_channels WHERE creator_id = ?",
            (creator_id,)
        )
        rows = self.db.cursor.fetchall()
        return [row[0] for row in rows]
