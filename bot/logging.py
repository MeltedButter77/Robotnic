import logging
from datetime import datetime
from config.paths import LOG_DIR


# Sends Discord messages to log events for the bot itself
# Channel stored in settings.json
class BotLogService:
    def __init__(self, bot):
        self.bot = bot

        self.settings = self.bot.settings.get("notifications", {})
        channel_id = self.settings.get("channel_id")
        self.channel = self.bot.get_channel(channel_id)

    async def send(self, event: str, message="", embed=None):
        if not self.channel:
            return

        # Checks if logging the event is enabled in settings.json
        if not self.settings.get(event, False):
            return

        await self.channel.send(message, embed=embed)


# Sends Discord messages to log events relevant to a single guild for moderation purposes
# Channel stored in database
class GuildLogService:
    def __init__(self, bot):
        self.bot = bot

    async def send(self, event: str, guild, message="", embed=None):
        channel = self.bot.get_channel(self.bot.repos.guild_settings.get_logs_channel_id(guild.id)["logs_channel_id"])
        if not channel:
            return

        await channel.send(message, embed=embed)


# Creates loggers for debug and info for the program itself
def setup_program_loggers(settings) -> logging.Logger:
    discord_debug = settings["debug"].get("discord", False)
    bot_debug = settings["debug"].get("bot", False)

    # File handler (shared)
    log_name = datetime.now()
    log_name = log_name.strftime("%Y-%m-%d-%H-%M-%S")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(filename=LOG_DIR / f"{log_name}.log", encoding='utf-8', mode='w')
    file_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))

    # Console handler (shared)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s: %(message)s'))

    # Pycord library logger
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.DEBUG if discord_debug else logging.INFO)

    # Bot logger
    logger = logging.getLogger('bot')
    logger.setLevel(logging.DEBUG if bot_debug else logging.INFO)

    # Attach handlers to the loggers
    discord_logger.addHandler(file_handler)
    discord_logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("Bot logger initialized")
    logger.debug("Bot logger debug mode active")
    discord_logger.info("Discord logger initialized")
    discord_logger.debug("Discord logger debug mode active")

    return logger
