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
                    owner_id INTEGER,
                    number INTEGER
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS temp_channel_hubs (
                    guild_id INTEGER,
                    channel_id INTEGER,
                    child_name TEXT,
                    user_limit INTEGER
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

    def get_child_name(self, channel_hub_id: int) -> str:
        """Retrieve the child name of a temporary channel hub."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('SELECT child_name FROM temp_channel_hubs WHERE channel_id = ?', (channel_hub_id,))
            return cursor.fetchone()[0]

    def get_user_limit(self, channel_hub_id: int) -> str:
        """Retrieve the child name of a temporary channel hub."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('SELECT user_limit FROM temp_channel_hubs WHERE channel_id = ?', (channel_hub_id,))
            return cursor.fetchone()[0]

    def add_temp_channel_hub(self, guild_id: int, channel_id: int, child_name: int, user_limit: int):
        """Add a new temporary channel hub to the database."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                'INSERT INTO temp_channel_hubs (guild_id, channel_id, child_name, user_limit) VALUES (?, ?, ?, ?)',
                (guild_id, channel_id, child_name, user_limit)
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

    def add_temp_channel(self, guild_id: int, channel_id: int, creator_id: int, owner_id: int, number: int):
        """Add a new temporary channel to the database."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                'INSERT INTO temp_channels (guild_id, channel_id, creator_id, owner_id, number) VALUES (?, ?, ?, ?, ?)',
                (guild_id, channel_id, creator_id, owner_id, number)
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

    def get_owner_id(self, temp_channel_id: int) -> int:
        """Get the owner ID of a temporary channel."""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('SELECT owner_id FROM temp_channels WHERE channel_id = ?', (temp_channel_id,))
            return cursor.fetchone()[0]


def createMenuEmbed(database, channels):
    embed = discord.Embed(
        title="Setup or Modify Channel Creators",
        description="Customise your channel creators to your specific need.",
        color=0x00ff00
    )
    embed.add_field(
        name="Current Creators:",
        value="",
        inline=False
    )
    for i, channel in enumerate(channels):
        child_name = database.get_child_name(channel.id)
        user_limit = database.get_user_limit(channel.id)
        if user_limit == 0:
            user_limit = "Unlimited"
        embed.add_field(
            name=f"#{i + 1}. {channel.mention}",
            value=f"Child Channel Names: `{child_name}`\nUser Limit: `{user_limit}`\n",
            inline=False
        )
    return embed


def createChannelEditEmbed(database, selected_channel):
    embed = discord.Embed(
        title=f"#{selected_channel.name}",
        description="",
        color=0x00ff00
    )
    embed.add_field(name="Name", value=selected_channel.name, inline=True)
    embed.add_field(name="Mention", value=selected_channel.mention, inline=True)
    embed.add_field(name="ID", value=str(selected_channel.id), inline=True)
    category = f"<#{selected_channel.category_id}>" if selected_channel.category_id else "None"
    embed.add_field(name="Category", value=category, inline=True)
    child_name = database.get_child_name(selected_channel.id)
    embed.add_field(name="Child Names", value=child_name, inline=True)
    user_limit = database.get_user_limit(selected_channel.id)
    if user_limit == 0:
        user_limit = "Unlimited"
    embed.add_field(name="User Limit", value=user_limit, inline=True)
    return embed


class CreatorSelectMenu(Select):
    """A dropdown menu for selecting a channel creator to edit."""

    def __init__(self,
            channels: List[discord.TextChannel],
            database: Database,
            bot: commands.Bot
    ):
        self.database = database
        self.bot = bot

        options = []
        if channels is not None:
            for i, channel in enumerate(channels):
                options.append(
                discord.SelectOption(
                    label=f"Modify Creator #{i + 1}",
                    description=f"{channel.name} ({channel.id})",
                    value=str(channel.id),
                    emoji="🔧"
                ))

        if len(options) <= 0:
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
            await interaction.response.send_message("Error: No creators available for select menu.", ephemeral=True)
            return

        selected_channel_id = int(self.values[0])
        selected_channel = self.bot.get_channel(selected_channel_id)

        # Create an embed with channel information
        embed = createChannelEditEmbed(self.database, selected_channel)

        # Create menu with channel hubs
        channel_ids = self.database.get_temp_channel_hubs(interaction.guild.id)
        channels = [self.bot.get_channel(channel_id) for channel_id in channel_ids]

        # Update the view to channel editor
        view = CreatorSelectView(
            modify_button=True,
            back_button=True,
            config=config,
            database=self.database,
            bot=self.bot
        )
        view.selected_channel_id = int(self.values[0])

        await interaction.response.edit_message(embed=embed, view=view)


class CreateCreatorModal(discord.ui.Modal, title="Create New Creator Channel"):
    def __init__(self, bot: commands.Bot, database: Database):
        super().__init__()
        self.bot = bot
        self.database = database

    # Define the text inputs
    child_name = discord.ui.TextInput(
        label="Channel Names (Variables: {user}, {count})",
        placeholder="Default: {user}'s Channel",
        required=False,
        max_length=25
    )
    user_limit = discord.ui.TextInput(
        label="User Limit (Unlimited = 0)",
        placeholder="Default: 0",
        required=False,
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Create a new voice channel and add it to the database
        channel = await interaction.guild.create_voice_channel(name="➕ Create Channel")
        temp_child_name = interaction.data["components"][0]["components"][0]["value"]
        if temp_child_name == "":
            temp_child_name = "{user}'s Channel"
        user_limit = interaction.data["components"][1]["components"][0]["value"]
        if user_limit == "":
            user_limit = 0
        else:
            user_limit = int(user_limit)
        self.database.add_temp_channel_hub(interaction.guild.id, channel.id, temp_child_name, user_limit)

        # Create an embed with channel information
        embed = createChannelEditEmbed(self.database, channel)

        # Update the view to channel editor
        view = CreatorSelectView(
            modify_button=True,
            back_button=True,
            config=config,
            database=self.database,
            bot=self.bot
        )

        await interaction.response.edit_message(embed=embed, view=view)


class EditCreatorModal(discord.ui.Modal, title="Edit Creator Channel"):
    def __init__(self, bot: commands.Bot, database: Database, edit_channel):
        super().__init__()
        self.bot = bot
        self.database = database
        self.edit_channel = edit_channel

    # Define the text inputs
    child_name = discord.ui.TextInput(
        label="Channel Names (Variables: {user}, {count})",
        placeholder="Default: {user}'s Channel",
        required=False,
        max_length=25
    )
    user_limit = discord.ui.TextInput(
        label="User Limit (Unlimited = 0)",
        placeholder="Default: 0",
        required=False,
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Create a new voice channel and add it to the database
        temp_child_name = interaction.data["components"][0]["components"][0]["value"]
        if temp_child_name == "":
            temp_child_name = "{user}'s Channel"
        user_limit = interaction.data["components"][1]["components"][0]["value"]
        if user_limit == "":
            user_limit = 0
        else:
            user_limit = int(user_limit)

        channel = self.edit_channel
        self.database.delete_temp_channel_hub(interaction.guild.id, channel.id)
        self.database.add_temp_channel_hub(interaction.guild.id, channel.id, temp_child_name, user_limit)

        # Create an embed with channel information
        embed = createChannelEditEmbed(self.database, channel)

        # Create menu with channel hubs
        channel_ids = self.database.get_temp_channel_hubs(interaction.guild.id)
        channels = [self.bot.get_channel(channel_id) for channel_id in channel_ids]

        # Update the view to channel editor
        view = CreatorSelectView(
            modify_button=True,
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
            modify_button=False,
            database: Database = None,
            bot: commands.Bot = None,
            selected_channel_id: int = None
    ):
        super().__init__()
        self.config = config
        self.selected_channel_id = selected_channel_id
        self.database = database
        self.bot = bot

        if menu_channels:
            self.add_item(CreatorSelectMenu(menu_channels, database=database, bot=bot))

        if modify_button:
            button = discord.ui.Button(
                label="Modify",
                style=discord.ButtonStyle.success
            )
            button.callback = self.modify_button_callback
            self.add_item(button)

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
        modal = CreateCreatorModal(self.bot, self.database)
        await interaction.response.send_modal(modal)

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
        embed = createMenuEmbed(self.database, channels)

        await interaction.response.edit_message(embed=embed, view=view)

    async def modify_button_callback(self, interaction: discord.Interaction):
        """Callback for the 'Modify existing creators' button."""
        selected_channel = self.bot.get_channel(self.selected_channel_id)
        modal = EditCreatorModal(self.bot, self.database, selected_channel)
        await interaction.response.send_modal(modal)


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

                child_name = str(self.database.get_child_name(after.channel.id))

                numbers = self.database.get_temp_channel_numbers(member.guild.id, after.channel.id)
                count = 1
                for i, value in enumerate(sorted(numbers)):
                    if value != i + 1:
                        count = i + 1
                        break
                    count = value + 1

                formatted_child_name = child_name.format(count=count, user=member.display_name)
                user_limit = self.database.get_user_limit(after.channel.id)
                if user_limit is None:
                    user_limit = 0
                channel = await member.guild.create_voice_channel(
                    name=formatted_child_name,
                    category=after.channel.category,
                    user_limit=user_limit,
                )

                self.database.add_temp_channel(
                    member.guild.id, channel.id, after.channel.id, member.id, count
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
        channels = [self.bot.get_channel(channel_id) for channel_id in channel_ids]
        view = CreatorSelectView(
            menu_channels=channels,
            create_button=True,
            website_button=True,
            config=self.config,
            database=self.database,
            bot=self.bot
        )

        # Create an embed with options
        embed = createMenuEmbed(self.database, channels)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    def cog_unload(self):
        """Cleanup when the cog is unloaded."""
        self.database.close()


async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(TempChannelsCommands(bot))
