
class CreatorChannelsRepository:
    def __init__(self, db, repos):
        self.db = db
        self.repos = repos

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

        self.db.cursor.execute(query, params)
        rows = self.db.cursor.fetchall()
        return [row[0] for row in rows]

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

        self.db.cursor.execute(query, tuple(values))
        self.db.connection.commit()

        return self.db.cursor.rowcount > 0  # Returns True if a row was updated

    def get_creator_channel_info(self, channel_id):
        self.db.cursor.execute("""
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
        self.db.cursor.execute("""
            INSERT OR REPLACE INTO creator_channels
            (guild_id, channel_id, child_name, user_limit, child_category_id, child_overwrites)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (guild_id, channel_id, child_name, user_limit, child_category_id, child_overwrites))
        self.db.connection.commit()


    def remove_creator_channel(self, channel_id):
        """
        Remove a temporary channel record by its channel_id.
        """
        self.db.cursor.execute(
            "DELETE FROM creator_channels WHERE channel_id = ?",
            (channel_id,)
        )
        self.db.connection.commit()
