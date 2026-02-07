import json


class GuildSettingsRepository:  # bot.repos.guild_settings
    def __init__(self, db, repos):
        self.db = db
        self.repos = repos

    def get(self, guild_id):
        self.db.cursor.execute("""
                            SELECT logs_channel_id, enabled_controls
                            FROM guild_settings
                            WHERE guild_id = ?
                            """, (guild_id,))
        row = self.db.cursor.fetchone()

        if row is None:
            # Add server to db
            self.add(guild_id, ["rename", "limit", "clear", "ban", "give", "delete"])
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

    def edit(self, guild_id: int, logs_channel_id: int = None, enabled_controls: str = None):
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

        self.db.cursor.execute(query, tuple(values))
        self.db.connection.commit()

        return self.db.cursor.rowcount > 0  # Returns True if a row was updated

    def get_logs_channel_id(self, guild_id):
        self.db.cursor.execute("""
                            SELECT logs_channel_id
                            FROM guild_settings
                            WHERE guild_id = ?
                            """, (guild_id,))
        row = self.db.cursor.fetchone()

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

    def get_profanity_filter(self, guild_id):
        self.db.cursor.execute("""
                            SELECT logs_channel_id
                            FROM guild_settings
                            WHERE guild_id = ?
                            """, (guild_id,))
        row = self.db.cursor.fetchone()

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

    def add(self, guild_id, default_enabled_controls=None):
        logs_channel_id = None
        enabled_controls_json = json.dumps(default_enabled_controls)
        self.db.cursor.execute("""
            INSERT OR REPLACE INTO guild_settings
            (guild_id, logs_channel_id, enabled_controls)
            VALUES (?, ?, ?)
        """, (guild_id, logs_channel_id, enabled_controls_json))
        self.db.connection.commit()
