import json
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import databasecontrol

load_dotenv()
token = str(os.getenv("TOKEN"))

# Load the configuration from config.json
base_directory = os.getenv('BASE_DIR', os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(base_directory, 'config.json')
# Load the configuration from config.json
with open(config_path) as config_file:
    config = json.load(config_file)

# Define the intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class Bot(commands.AutoShardedBot):  # Use AutoShardedBot for scalability
    def __init__(self):
        super().__init__(command_prefix='/', intents=intents)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')

        server_count = len(bot.guilds)
        await bot.change_presence(activity=discord.CustomActivity(name=f"Online in {server_count} Servers"))

        await self.setup_cogs()
        await self.send_notification()

    async def load_extension_with_args(self, cog_name, *args):
        cog = __import__(cog_name, fromlist=['setup'])
        await cog.setup(self, *args)

    async def setup_cogs(self):
        db_path = os.path.join(base_directory, 'temp_channels.db')
        database = databasecontrol.Database(db_path)
        database.connect()

        # Load cogs/extensions
        await self.load_extension("cogs.utils")
        await self.load_extension_with_args("cogs.tempchannels.manage", database)
        await self.load_extension_with_args("cogs.tempchannels.control", database)
        print("Loaded extensions successfully!")

    async def send_notification(self):
        # Channel notification for syncing
        if self.user.id == 853490879753617458:
            notification_channel = self.get_channel(int(config["sync_channel_id"]))
        else:
            notification_channel = self.get_channel(int(config["testing_sync_channel_id"]))
        if notification_channel is not None:
            await notification_channel.send('Syncing...')
            synced_commands = await self.tree.sync()
            await notification_channel.send(f'Synced {len(synced_commands)} commands!')
        print("Synced the commands")

# Create the bot instance
bot = Bot()

# Run the bot
bot.run(token)
