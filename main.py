import asyncio
import inspect
import json
import os
import sys
import discord
import logging
import dotenv

import coroutine_tasks
import handle_voice
from database import Database

# Main.py Logic Structure
# 1. Set Directories
# 2. Retrieve Settings.json
# 3. Initialize Discord and App loggers
# 4. Retrieve bot token
# 5. Bot class, handles all bot methods
# 6. Initialize Bot object and set a database object as an attribute
# 7. Commands as decorated functions, triggers relevant code
# 8. Run bot


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
logger = logging.getLogger('app')
logger.setLevel(logging.DEBUG if app_debug else logging.INFO)

# Attach handlers to the loggers
discord_logger.addHandler(file_handler)
discord_logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("App logger initialized")
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
class Bot(discord.Bot):
    def __init__(self, token):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.token = token

    async def on_ready(self):
        logger.info(f'Logged in as {self.user}')
        await coroutine_tasks.create_tasks(self, logger)

    async def on_voice_state_update(self, member, before, after):
        await handle_voice.update(member, before, after, bot=bot, logger=logger)

    async def on_message(self, message):
        # Ignore self messages from bot
        if message.author == self.user:
            return

        # Ping command
        if message.content.lower() == "!ping":
            logger.debug(f"!ping triggered by {message.author}")
            await message.channel.send("Pong!")

    async def on_application_command_error(self, ctx, exception):
        if isinstance(exception.original, discord.Forbidden):
            await ctx.send("I require more permissions.")
        else:
            logger.error(f"ERROR\nContext: {ctx}\nException: {exception}")
            await ctx.send("Error, check logs.")

    def run(self):
        try:
            super().run(self.token)
        except Exception as e:
            logger.error(
                "Could not log in. Invalid TOKEN. "
                "Please replace 'TOKEN_HERE' with your actual bot token."
            )
            sys.exit(1)


bot = Bot(client_token)
bot.db = Database("database.db")


@bot.command(description="Sends the bot's latency.")
async def ping(ctx):
    await ctx.respond(f"Pong! Latency is {bot.latency}")


@bot.command(description="Create a new Creator Channel")
async def creator(ctx):
    new_creator_channel = await ctx.guild.create_voice_channel("➕ Create Channel")
    bot.db.add_creator_channel(new_creator_channel.guild.id, new_creator_channel.id, "temp channel", 0, 0)
    await ctx.respond(f"Your creator is {new_creator_channel.mention}")


bot.run()
