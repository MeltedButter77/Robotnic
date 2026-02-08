import json

defaults = {
    "guild_id": None,
    "logs_channel_id": None,
    "enabled_controls": ["rename", "limit", "clear", "ban", "give", "delete"],
    "mention_owner_bool": 0,
    "profanity_filter": "alert",
    "enabled_log_events": ["channel_create", "channel_rename", "channel_remove ", "profanity_block"],
    "control_options": ["dropdown", "labels"],
}


class GuildSettingsRepository:  # bot.repos.guild_settings
    def __init__(self, db, repos):
        self.db = db
        self.repos = repos

    def get(self, guild_id):
        self.db.cursor.execute("""
                            SELECT logs_channel_id, enabled_controls, mention_owner_bool, profanity_filter, enabled_log_events, control_options
                            FROM guild_settings
                            WHERE guild_id = ?
                            """, (guild_id,))
        row = self.db.cursor.fetchone()

        if row is None:
            # return Default settings, keys matching database
            defaults["guild_id"] = guild_id
            return defaults

        (
            logs_channel_id,
            enabled_controls_json,
            mention_owner_bool,
            profanity_filter,
            enabled_log_events_json,
            control_options_json
        ) = row

        enabled_controls = json.loads(enabled_controls_json) if enabled_controls_json else {}
        enabled_log_events = json.loads(enabled_log_events_json) if enabled_log_events_json else {}
        control_options = json.loads(control_options_json) if control_options_json else {}

        return {
            "guild_id": guild_id,
            "logs_channel_id": logs_channel_id,
            "enabled_controls": enabled_controls,
            "mention_owner_bool": bool(mention_owner_bool),
            "profanity_filter": profanity_filter,
            "enabled_log_events": enabled_log_events,
            "control_options": control_options
        }

    def edit(
            self,
            guild_id: int,
            logs_channel_id: int = None,
            enabled_controls: str = None,
            mention_owner: bool = None,
            profanity_filter: str = None,
            enabled_log_events: str = None,
            control_options: str = None,
        ):
        # Check if the server has an entry
        self.db.cursor.execute("""
                               SELECT logs_channel_id
                               FROM guild_settings
                               WHERE guild_id = ?
                               """, (guild_id,))
        row = self.db.cursor.fetchone()
        if not row:
            self.add(
                guild_id=guild_id
            )

        fields = []
        values = []

        if logs_channel_id is not None:
            fields.append("logs_channel_id = ?")
            values.append(logs_channel_id)

        if enabled_controls is not None:
            fields.append("enabled_controls = ?")
            values.append(json.dumps(enabled_controls))

        if mention_owner is not None:
            fields.append("mention_owner_bool = ?")
            values.append(1 if mention_owner else 0)

        if profanity_filter is not None:
            fields.append("profanity_filter = ?")
            values.append(None if profanity_filter == "off" else profanity_filter)

        if enabled_log_events is not None:
            fields.append("enabled_log_events = ?")
            values.append(json.dumps(enabled_log_events))

        if control_options is not None:
            fields.append("control_options = ?")
            values.append(json.dumps(control_options))

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
                            SELECT profanity_filter
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

        profanity_filter = row[0]

        return {
            "guild_id": guild_id,
            "profanity_filter": profanity_filter,
        }

    def add(self, guild_id):
        logs_channel_id = defaults["logs_channel_id"]
        enabled_controls_json = json.dumps(defaults["enabled_controls"])
        mention_owner_bool = defaults["mention_owner_bool"]
        profanity_filter = defaults["profanity_filter"]
        enabled_log_events_json = json.dumps(defaults["enabled_log_events"])

        self.db.cursor.execute("""
            INSERT OR REPLACE INTO guild_settings
            (guild_id, logs_channel_id, enabled_controls, mention_owner_bool, profanity_filter, enabled_log_events)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (guild_id, logs_channel_id, enabled_controls_json, bool(mention_owner_bool), profanity_filter, enabled_log_events_json))
        self.db.connection.commit()
