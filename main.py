import json
import os
import sys
import discord
import logging
import dotenv
from handle_voice import user_join, user_move, user_leave
from database import Database

# Directories
script_dir = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(script_dir, 'discord.log')
env_path = os.path.join(script_dir, '.env')
settings_path = os.path.join(script_dir, "settings.json")

# Default settings
default_settings = {
    "logging": {
        "discord": False,
        "app": False
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
app_debug = settings["logging"].get("app", False)

# File handler (shared)
file_handler = logging.FileHandler(filename=log_path, encoding='utf-8', mode='w')
file_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))

# Console handler (shared)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s: %(message)s'))

# Pycord library logger
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.DEBUG if discord_debug else logging.INFO)

# Application logger
app_logger = logging.getLogger('app')
app_logger.setLevel(logging.DEBUG if app_debug else logging.INFO)

# Attach handlers to the loggers
discord_logger.addHandler(file_handler)
discord_logger.addHandler(console_handler)
app_logger.addHandler(file_handler)
app_logger.addHandler(console_handler)

app_logger.info("App logger initialized")
discord_logger.info("Discord logger initialized")

# Check if .env exists, if not create a new one
placeholder = "TOKEN_HERE"
if not os.path.exists(env_path):
    with open(env_path, 'w') as f:
        f.write(f"TOKEN={placeholder}\n")
    app_logger.error(
        "No .env file found, one has been created. "
        "Please replace 'TOKEN_HERE' with your actual bot token."
    )
    sys.exit(1)
else:
    app_logger.debug(
        "Valid .env file found. "
    )

# Get Token
dotenv.load_dotenv()
client_token = os.getenv("TOKEN")
# Handle placeholder or no token
if client_token == placeholder or not client_token:
    app_logger.error(
        "No valid TOKEN found in .env. "
        "Please replace 'TOKEN_HERE' with your actual bot token."
    )
    sys.exit(1)
else:
    app_logger.debug(
        "Token found. "
    )


# Subclassed discord.Client allowing for methods to correspond directly with bot triggers
class Bot(discord.Bot):
    def __init__(self, token):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.token = token

    async def on_ready(self):
        app_logger.info(f'Logged in as {self.user}')

    async def on_message(self, message):
        # Ignore self messages from bot
        if message.author == self.user:
            return

        # Ping command
        if message.content.lower() == "!ping":
            app_logger.debug(f"!ping triggered by {message.author}")
            await message.channel.send("Pong!")

    def run(self):
        try:
            super().run(self.token)
        except Exception as e:
            app_logger.error(
                "Could not log in. Invalid TOKEN. "
                "Please replace 'TOKEN_HERE' with your actual bot token."
            )
            sys.exit(1)


bot = Bot(client_token)
bot.db = Database("database.db")


@bot.command(description="Sends the bot's latency.")
async def ping(ctx):
    await ctx.respond(f"Pong! Latency is {bot.latency}")


@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None and after.channel is not None:
        await user_join(member, before, after, bot=bot, logger=app_logger)
    elif before.channel and after.channel and before.channel != after.channel:
        await user_move(member, before, after, bot=bot, logger=app_logger)
    elif before.channel and after.channel is None:
        await user_leave(member, before, after, bot=bot, logger=app_logger)


bot.run()
