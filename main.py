import json
import os
import sys
import discord
import logging
import dotenv
from database import Database
from pathlib import Path
from datetime import datetime

# Main.py Logic Structure
# 1. Set Directories
# 2. Retrieve Settings.json
# 3. Initialize Discord and Bot loggers
# 4. Retrieve bot token
# 5. Bot class, handles all bot methods
# 6. Initialize Bot object and set a database object as an attribute
# 7. Run bot


# Directories
script_dir = Path(__file__).parent
log_path = script_dir / "logs"
log_path.mkdir(exist_ok=True)
env_path = script_dir / ".env"
settings_path = script_dir / "settings.json"

# Default settings
default_settings = {
    "logging": {
        "discord": False,
        "bot": False
    },
    "notifications": {
        "channel_id": None
    },
    "control_message": {
        "labeled_icons": True,
        "icon_description_embed": False
    }
}

# Create settings file if it doesn't exist
if not os.path.exists(settings_path):
    with open(settings_path, "w") as f:
        json.dump(default_settings, f, indent=4)
    print(f"Created default settings.json at {settings_path}. Edit to change debug settings.")

# Load settings
with open(settings_path, "r") as f:
    settings = json.load(f)
discord_debug = settings["logging"].get("discord", False)
bot_debug = settings["logging"].get("bot", False)

# Import after settings have been made
import coroutine_tasks
from cogs import creator_menu, voice_logic

# File handler (shared)
log_name = datetime.now()
log_name = log_name.strftime("%Y-%m-%d-%H-%M-%S")
file_handler = logging.FileHandler(filename=log_path / f"{log_name}.log", encoding='utf-8', mode='w')
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
discord_logger.info("Discord logger initialized")

# Check if .env exists, if not create a new one
placeholder = "TOKEN_HERE"
if not os.path.exists(env_path):
    with open(env_path, 'w') as f:
        f.write(f"TOKEN={placeholder}\n")
    logger.error(
        "No .env file found, one has been created. "
        "Please replace 'TOKEN_HERE' with your actual bot token."
    )
    sys.exit(1)
else:
    logger.debug(
        "Valid .env file found. "
    )

# Get Token
dotenv.load_dotenv()
client_token = os.getenv("TOKEN")
# Handle placeholder or no token
if client_token == placeholder or not client_token:
    logger.error(
        "No valid TOKEN found in .env. "
        "Please replace 'TOKEN_HERE' with your actual bot token."
    )
    sys.exit(1)
else:
    logger.debug(
        "Token found. "
    )


# Subclassed discord.Bot allowing for methods to correspond directly with bot triggers
class Bot(discord.AutoShardedBot):
    def __init__(self, token, logger, database):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.presences = True
        intents.members = True
        super().__init__(intents=intents)
        self.token = token
        self.logger = logger
        self.db = database
        self.notification_channel = None
        self.renamer = voice_logic.TempChannelRenamer(self)

    async def on_ready(self):
        self.logger.info(f'Logged in as {self.user}')
        await coroutine_tasks.create_tasks(self)
        await bot.sync_commands()
        self.logger.info(f'Commands synced')

        self.notification_channel = self.get_channel(settings["notifications"].get("channel_id", None))
        if self.notification_channel:
            await self.notification_channel.send(f"Bot {self.user.mention} started.")

    async def close(self):
        self.logger.info(f'Logging out {self.user}')

        # Update all control messages with a disabled button saying its expired
        for temp_channel_id in self.db.get_temp_channel_ids():
            temp_channel = self.get_channel(temp_channel_id)
            # Searches first 10 messages for first send by the bot. This will almost always be the creator
            async for control_message in temp_channel.history(limit=10, oldest_first=True):
                if control_message.author.id == bot.user.id:
                    # Create a new view with one disabled button
                    view = discord.ui.View()
                    view.add_item(
                        discord.ui.Button(
                            label="This control message has expired",
                            style=discord.ButtonStyle.secondary,
                            disabled=True
                        )
                    )
                    # Edit the message to show the new view
                    await control_message.edit(view=view)

        if self.notification_channel:
            await self.notification_channel.send(f"Bot {self.user.mention} stopping.")
        await super().close()

    async def on_application_command_error(self, ctx, exception):
        if isinstance(exception.original, discord.Forbidden):
            await ctx.send("I require more permissions.")
        else:
            self.logger.error(f"ERROR in {__name__}\nContext: {ctx}\nException: {exception}")
            await ctx.send("Error, check logs. Type: on_application_command_error")

    def run(self):
        try:
            super().run(self.token)
        except Exception as e:
            self.logger.error(
                "Could not log in. Invalid TOKEN. "
                "Please replace 'TOKEN_HERE' with your actual bot token."
            )
            sys.exit(1)


bot = Bot(client_token, logger, Database("database.db"))
# Load all cogs from /cogs
for filename in os.listdir("./cogs"):
    if filename.endswith(".py") and not filename.startswith("_"):
        bot.load_extension(f"cogs.{filename[:-3]}")
        bot.logger.debug(f"Loaded cog: {filename}")


bot.run()
