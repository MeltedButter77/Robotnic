from discord.ui import Modal, Select, View, select
import json
import os
import sys
import discord
import logging
import dotenv
import coroutine_tasks
import creator_command
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
    },
    "notifications": {
        "channel_id": None
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
        self.renamer = handle_voice.TempChannelRenamer(self)

    async def on_ready(self):
        logger.info(f'Logged in as {self.user}')
        await coroutine_tasks.create_tasks(self)

        self.notification_channel = self.get_channel(settings["notifications"].get("channel_id", None))
        if self.notification_channel:
            await self.notification_channel.send(f"Bot {self.user.mention} started.")

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

    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        # Updates temp channel name if child_name_template has activities and a connected user changes activities
        if after.voice and after.voice.channel:
            temp_channel = after.voice.channel

            db_temp_channel_info = bot.db.get_temp_channel_info(temp_channel.id)
            if not db_temp_channel_info:
                return
            db_creator_channel_info = bot.db.get_creator_channel_info(db_temp_channel_info.creator_id)
            if db_temp_channel_info is not None and "{activity}" in str(db_creator_channel_info.child_name):
                new_channel_name = handle_voice.create_temp_channel_name(bot, temp_channel)
                # If the current name is different to the correct name, rename it.
                if temp_channel.name != new_channel_name:
                    bot.logger.debug(f"Renaming {temp_channel.name} to {new_channel_name} due to activity change")
                    await bot.renamer.schedule_name_update(temp_channel, new_channel_name)

    async def on_application_command_error(self, ctx, exception):
        if isinstance(exception.original, discord.Forbidden):
            await ctx.send("I require more permissions.")
        else:
            logger.error(f"ERROR in {__name__}\nContext: {ctx}\nException: {exception}")
            await ctx.send("Error, check logs. Type: on_application_command_error")

    def run(self):
        try:
            super().run(self.token)
        except Exception as e:
            logger.error(
                "Could not log in. Invalid TOKEN. "
                "Please replace 'TOKEN_HERE' with your actual bot token."
            )
            sys.exit(1)


bot = Bot(client_token, logger, Database("database.db"))


@bot.command(description="Sends the bot's latency.")
async def ping(ctx):
    await ctx.respond(f"Pong! Latency is {bot.latency}")


@bot.command(description="Create a new Creator Channel")
async def creator(ctx):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send_response(f"Sorry {ctx.author.mention}, you require the `administrator` permission to run this command.")

    embeds = [
        creator_command.OptionsEmbed(guild=ctx.guild, bot=bot),
        creator_command.ListCreatorsEmbed(guild=ctx.guild, bot=bot),
    ]
    view = creator_command.CreateView(ctx=ctx, bot=bot)
    message = await ctx.send_response(f"{ctx.author.mention}", embeds=embeds, view=view)  # , ephemeral=True)
    view.message = message


bot.run()
