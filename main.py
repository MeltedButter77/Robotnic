import json
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import databasecontrol
from topgg import DBLClient

load_dotenv()
token = str(os.getenv("TOKEN"))
topgg_token = str(os.getenv("TOPGG_TOKEN"))

# Load the configuration from config.json
base_directory = os.getenv('BASE_DIR', os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(base_directory, 'config.json')
# Load the configuration from config.json
with open(config_path) as config_file:
    config = json.load(config_file)

# Define the intents
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True


class Bot(commands.AutoShardedBot):  # Use AutoShardedBot for scalability
    def __init__(self):
        super().__init__(command_prefix='/', intents=intents)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')

        await self.init_topgg()

        await self.setup_cogs()
        await self.send_notification()
        self.update_server_count.start()  # Start the server count update loop

    async def init_topgg(self):
        self.topgg_client = DBLClient(self, topgg_token)  # Initialize the Top.gg client

    @tasks.loop(hours=12)  # Update the server count every 30 minutes
    async def update_server_count(self):
        try:
            total_users = 0
            for server in self.guilds:
                total_users += server.member_count

            server_count = len(self.guilds)
            await self.change_presence(activity=discord.CustomActivity(name=f"Online in {server_count} Servers | {total_users} Users"))
            print(f"Updated server count ({server_count}) and user count ({total_users}) to status")

            if self.user.id == 853490879753617458:
                await self.topgg_client.post_guild_count()  # Post the server count to Top.gg
                print(f"Posted server count ({server_count}) to Top.gg!")
        except Exception as e:
            print(f"Failed to post server count to Top.gg: {e}")

    async def on_guild_join(self, guild):
        # This event is triggered when the bot joins a new guild
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                embed = discord.Embed(
                    title=f"Hello {guild.name}! 🎉",
                    description="Thank you for inviting me to your server! 😊\nHere are some commands to get started.",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="/setup_creators",
                    value="Allows an admin to setup a channel creator (or channel hub) which dynamically creates voice channels when users join them.",
                    inline=False
                )
                embed.set_footer(text="Need more help? Reach out to support below!")
                view = discord.ui.View()
                view.add_item(discord.ui.Button(style=discord.ButtonStyle.url,
                                                label="Contact Support",
                                                url=f"{config['support_server']}"))
                view.add_item(discord.ui.Button(style=discord.ButtonStyle.url,
                                                label="Visit Website",
                                                url=f"{config['website']}"))
                await channel.send(embed=embed, view=view)
                break

        if self.user.id == 853490879753617458:
            notification_channel = self.get_channel(int(config["sync_channel_id"]))
        else:
            notification_channel = self.get_channel(int(config["testing_sync_channel_id"]))
        if notification_channel is not None:
            # Get the guild information
            guild_name = guild.name
            guild_id = guild.id
            guild_owner = guild.owner
            guild_owner_id = guild.owner_id
            guild_member_count = guild.member_count
            guild_creation_date = guild.created_at.strftime("%Y-%m-%d %H:%M:%S")
            guild_region = str(guild.preferred_locale)  # If you want locale info

            # Create the embed with the server information
            embed = discord.Embed(
                title="Joined a New Server!",
                description=f"",
                color=discord.Color.green()
            )

            embed.add_field(name="Server Name", value=guild_name, inline=True)
            embed.add_field(name="Server ID", value=guild_id, inline=True)
            embed.add_field(name="Owner", value=f"{guild_owner} (ID: {guild_owner_id})", inline=True)
            embed.add_field(name="Member Count", value=guild_member_count, inline=True)
            embed.add_field(name="Creation Date", value=guild_creation_date, inline=True)
            embed.add_field(name="Region/Locale", value=guild_region, inline=True)

            # Send the information to the notification channel
            await notification_channel.send(embed=embed)

    async def load_extension_with_args(self, cog_name, *args):
        cog = __import__(cog_name, fromlist=['setup'])
        await cog.setup(self, *args)

    async def setup_cogs(self):
        db_path = os.path.join(base_directory, 'temp_channels.db')
        database = databasecontrol.Database(db_path)
        database.connect()

        # Load cogs/extensions
        print("Unloading extensions")
        try:
            await self.unload_extension("cogs.utils")
        except commands.ExtensionNotLoaded:
            pass  # Ignore if not loaded
        try:
            await self.unload_extension("cogs.tempchannels.manage")
        except commands.ExtensionNotLoaded:
            pass
        try:
            await self.unload_extension("cogs.tempchannels.control")
        except commands.ExtensionNotLoaded:
            pass

        # Now safely reload them
        print("Loading extensions")
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
