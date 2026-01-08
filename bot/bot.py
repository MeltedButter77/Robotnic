import os
import sys
import discord
from topgg import DBLClient
from cogs.manage_vcs.renamer import TempChannelRenamer
from bot.events.ready import on_ready
from bot.events.guild_join import on_guild_join
from bot.events.errors import on_application_command_error
from bot.events.close import close


class Bot(discord.AutoShardedBot):
    def __init__(self, token, topgg_token, logger, database, settings):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.presences = True
        intents.members = True
        super().__init__(intents=intents)

        self.token = token
        self.logger = logger
        self.db = database
        self.settings = settings

        self.notification_channel = self.get_channel(self.settings["notifications"].get("channel_id", None))
        self.renamer = TempChannelRenamer(self)

        self.topgg_client = DBLClient(self, topgg_token) if topgg_token else None

    # Sends logs in the discord channel selected in settings.json under "notifications": "channel_id":
    async def send_bot_log(self, type, message, embeds=None):
        if self.notification_channel and self.settings["notifications"].get(str(type), False):
            await self.notification_channel.send(message, embeds=embeds)

    # Load all cogs from /cogs
    def _load_cogs(self):
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                self.load_extension(f"cogs.{filename[:-3]}")
                self.logger.debug(f"Loaded cog: {filename}")

    def run(self):
        self._load_cogs()

        try:
            super().run(self.token)
        except Exception as e:
            self.logger.error(
                "Could not log in. Invalid TOKEN. "
                "Please replace 'TOKEN_HERE' with your actual bot token."
            )
            sys.exit(1)

    # Events
    async def on_ready(self):
        await on_ready(self)

    async def close(self):
        await close(self)
        await super().close()

    async def on_guild_join(self, guild):
        await on_guild_join(self, guild)

    async def on_application_command_error(self, ctx, exception):
        await on_application_command_error(self, ctx, exception)
