import json
import discord
from discord.ext import commands

# Load the token from config.json
with open('config.json') as config_file:
    config = json.load(config_file)
token = config['token']

# Define the intents
intents = discord.Intents.default()

# Create a bot instance
bot = commands.Bot(intents=intents)

# Print "Hello World"
print("Hello World")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}#{bot.user.discriminator}!')

    # Sync the command tree to register slash commands
    try:
        synced = await bot.tree.sync()
        print(f'Successfully synced {len(synced)} commands.')
    except Exception as e:
        print(f'Error syncing commands: {e}')

@bot.tree.command(name="ping", description="Replies with Pong!")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

# Run the bot
bot.run(token)
