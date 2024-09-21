import json
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()
token = str(os.getenv("TOKEN"))

# Load the token from config.json
with open('config.json') as config_file:
    config = json.load(config_file)

# Define the intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Create a bot instance
bot = commands.Bot(intents=intents, command_prefix="/")

intents.members = True
intents.message_content = True
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

    # Loads commands from the extensions
    await bot.load_extension("utils")
    await bot.load_extension("channels")
    print("Loaded extensions successfully!")

# Run the bot
bot.run(token)
