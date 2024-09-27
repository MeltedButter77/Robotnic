import sqlite3
from typing import List
import discord
from discord.ext import commands
from discord.ui import Select, View
import json
import os

# Get the absolute path to the config.json
base_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # One level up
config_path = os.path.join(base_directory, 'config.json')
# Load the configuration from config.json
with open(config_path) as config_file:
    config = json.load(config_file)


class Database:
    """A class to handle all database operations."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Connect to the SQLite database and ensure tables exist."""
        self.connection = sqlite3.connect(self.db_path)
        self._ensure_tables()

    def _ensure_tables(self):
        """Create necessary tables if they do not exist."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS temp_channels (
                    guild_id INTEGER,
                    channel_id INTEGER,
                    creator_id INTEGER,
                    number INTEGER
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS temp_channel_hubs (
                    guild_id INTEGER,
                    channel_id INTEGER
                )
            """)

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()

    def get_temp_channel_hubs(self, guild_id: int) -> List[int]:
        """Retrieve all temporary channel hub IDs for a guild."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('SELECT channel_id FROM temp_channel_hubs WHERE guild_id = ?', (guild_id,))
            return [row[0] for row in cursor.fetchall()]

    def add_temp_channel_hub(self, guild_id: int, channel_id: int):
        """Add a new temporary channel hub to the database."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                'INSERT INTO temp_channel_hubs (guild_id, channel_id) VALUES (?, ?)',
                (guild_id, channel_id)
            )

    def delete_temp_channel_hub(self, guild_id: int, channel_id: int):
        """Delete a temporary channel hub from the database."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                'DELETE FROM temp_channel_hubs WHERE guild_id = ? AND channel_id = ?',
                (guild_id, channel_id)
            )

    def get_temp_channel_numbers(self, guild_id: int, creator_id: int) -> List[int]:
        """Get all temporary channel numbers for a guild and creator."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                'SELECT number FROM temp_channels WHERE guild_id = ? AND creator_id = ?',
                (guild_id, creator_id)
            )
            return [row[0] for row in cursor.fetchall()]

    def add_temp_channel(self, guild_id: int, channel_id: int, creator_id: int, number: int):
        """Add a new temporary channel to the database."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                'INSERT INTO temp_channels (guild_id, channel_id, creator_id, number) VALUES (?, ?, ?, ?)',
                (guild_id, channel_id, creator_id, number)
            )

    def delete_temp_channel(self, channel_id: int):
        """Delete a temporary channel from the database."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('DELETE FROM temp_channels WHERE channel_id = ?', (channel_id,))

    def is_temp_channel(self, channel_id: int) -> bool:
        """Check if a channel is a temporary channel."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('SELECT 1 FROM temp_channels WHERE channel_id = ?', (channel_id,))
            return cursor.fetchone() is not None


class CreatorSelectMenu(Select):
    """A dropdown menu for selecting a channel creator to edit."""

    def __init__(self,
            channels: List[discord.TextChannel],
            database: Database,
            bot: commands.Bot
    ):
        self.database = database
        self.bot = bot

        options = [
            discord.SelectOption(
                label=f"#{channel.name} ({channel.id})",
                value=str(channel.id),
                emoji="🔧"
            ) for channel in channels
        ]

        if not options:
            options = [
                discord.SelectOption(label="None", value="None", emoji="🔧")
            ]
            super().__init__(
                placeholder="No creators to select",
                options=options,
                disabled=True,
                min_values=1,
                max_values=1
            )
        else:
            super().__init__(
                placeholder="Select a creator to edit",
                options=options,
                min_values=1,
                max_values=1
            )

    async def callback(self, interaction: discord.Interaction):
        """Handle the selection of a channel creator."""
        if self.values[0] == "None":
            await interaction.response.send_message("No creators available to select.", ephemeral=True)
            return

        selected_channel_id = int(self.values[0])
        selected_channel = self.bot.get_channel(selected_channel_id)

        # Create an embed with channel information
        embed = discord.Embed(
            title=f"#{selected_channel.name}",
            description="This channel is cool",
            color=0x00ff00
        )
        embed.add_field(name="Name", value=selected_channel.name, inline=True)
        embed.add_field(name="ID", value=str(selected_channel.id), inline=True)
        category = f"<#{selected_channel.category_id}>" if selected_channel.category_id else "None"
        embed.add_field(name="Category", value=category, inline=True)

        # Update the view to channel editor
        view = CreatorSelectView(
            back_button=True,
            config=config,
            database=self.database,
            bot=self.bot
        )

        await interaction.response.edit_message(embed=embed, view=view)


class CreatorSelectView(View):
    """A view containing buttons and menus for managing channel creators."""

    def __init__(self,
            menu_channels: List[discord.TextChannel] = None,
            create_button: bool = False,
            website_button: bool = False,
            back_button: bool = False,
            config=None,
            database: Database = None,
            bot: commands.Bot = None
    ):
        super().__init__()
        self.config = config
        self.database = database
        self.bot = bot

        if menu_channels:
            self.add_item(CreatorSelectMenu(menu_channels, database=database, bot=bot))

        if create_button:
            button = discord.ui.Button(
                label="Create new Creator",
                style=discord.ButtonStyle.success
            )
            button.callback = self.create_button_callback
            self.add_item(button)

        if website_button and config:
            self.add_item(discord.ui.Button(
                label="Website",
                url=config['website'],
                style=discord.ButtonStyle.link
            ))

        if back_button:
            button = discord.ui.Button(
                label="Back",
                style=discord.ButtonStyle.secondary
            )
            button.callback = self.back_button_callback
            self.add_item(button)

    async def create_button_callback(self, interaction: discord.Interaction):
        """Callback for the 'Create new Creator' button."""
        # Create a new voice channel and add it to the database
        channel = await interaction.guild.create_voice_channel(name="➕ Create Channel")
        self.database.add_temp_channel_hub(interaction.guild.id, channel.id)

        # Create an embed with channel information
        embed = discord.Embed(
            title=f"#{channel.name}",
            description="This channel is cool",
            color=0x00ff00
        )
        embed.add_field(name="Name", value=channel.name, inline=True)
        embed.add_field(name="ID", value=str(channel.id), inline=True)
        category = f"<#{channel.category_id}>" if channel.category_id else "None"
        embed.add_field(name="Category", value=category, inline=True)

        # Update the view to channel editor
        view = CreatorSelectView(
            back_button=True,
            config=config,
            database=self.database,
            bot=self.bot
        )

        await interaction.response.edit_message(embed=embed, view=view)

    async def back_button_callback(self, interaction: discord.Interaction):
        """Callback for the 'Back' button."""
        # Update the menu with channel hubs
        channel_ids = self.database.get_temp_channel_hubs(interaction.guild.id)
        channels = [self.bot.get_channel(cid) for cid in channel_ids]
        view = CreatorSelectView(
            menu_channels=channels,
            create_button=True,
            website_button=True,
            config=self.config,
            database=self.database,
            bot=self.bot
        )

        # Create an embed with options
        embed = discord.Embed(
            title="Channel Hub Setup",
            description="Choose an option to set the channel hub.",
            color=0x00ff00
        )
        embed.add_field(
            name="Options",
            value="You can choose one of the options from the dropdown below.",
            inline=False
        )

        await interaction.response.edit_message(embed=embed, view=view)


class TempChannelsCommands(commands.Cog):
    """A cog that manages temporary voice channels."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = config
        db_path = os.path.join(base_directory, 'temp_channels.db')
        self.database = Database(db_path)
        self.database.connect()

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Listener to handle deletion of channel hubs."""
        self.database.delete_temp_channel_hub(channel.guild.id, channel.id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Listener to handle creation and deletion of temporary channels."""
        if after.channel:
            # Create temporary channel if member joins a hub channel
            channel_hub_ids = self.database.get_temp_channel_hubs(member.guild.id)
            if after.channel.id in channel_hub_ids:
                numbers = self.database.get_temp_channel_numbers(member.guild.id, after.channel.id)
                channel_number = 1
                for i, value in enumerate(sorted(numbers)):
                    if value != i + 1:
                        channel_number = i + 1
                        break
                    channel_number = value + 1

                channel_name = f"Lobby {channel_number}"
                channel = await member.guild.create_voice_channel(
                    name=channel_name,
                    category=after.channel.category
                )

                self.database.add_temp_channel(
                    member.guild.id, channel.id, after.channel.id, channel_number
                )
                await member.move_to(channel)

        if before.channel:
            # Delete temporary channel if empty
            if self.database.is_temp_channel(before.channel.id) and len(before.channel.members) == 0:
                left_channel = self.bot.get_channel(before.channel.id)
                if left_channel:
                    await left_channel.delete()
                self.database.delete_temp_channel(before.channel.id)

    @discord.app_commands.command(
        name="setup_creators",
        description="Create and edit Channel Hubs."
    )
    async def setup_creators(self, interaction: discord.Interaction):
        """Command to set up channel creators."""
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                f"Sorry {interaction.user.mention}, you require the `manage_channels` permission to use that command.",
                ephemeral=True
            )
            return

        # Create menu with channel hubs
        channel_ids = self.database.get_temp_channel_hubs(interaction.guild.id)
        channels = [self.bot.get_channel(cid) for cid in channel_ids]
        view = CreatorSelectView(
            menu_channels=channels,
            create_button=True,
            website_button=True,
            config=self.config,
            database=self.database,
            bot=self.bot
        )

        # Create an embed with options
        embed = discord.Embed(
            title="Channel Hub Setup",
            description="Choose an option to set the channel hub.",
            color=0x00ff00
        )
        embed.add_field(
            name="Options",
            value="You can choose one of the options from the dropdown below.",
            inline=False
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    def cog_unload(self):
        """Cleanup when the cog is unloaded."""
        self.database.close()


async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(TempChannelsCommands(bot))
