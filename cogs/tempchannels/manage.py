import asyncio
from discord import app_commands
import databasecontrol
from error_handling import handle_bot_permission_error, handle_command_error, handle_global_error, \
    handle_user_permission_error
import cogs.tempchannels.control
from typing import List
import discord
from discord.ext import commands
from discord.ui import Select, View
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

base_directory = os.getenv('BASE_DIR', os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(base_directory, 'config.json')
# Load the configuration from config.json
with open(config_path) as config_file:
    config = json.load(config_file)


class SelectCreatorView(View):
    """A view containing buttons and menus for managing channel creators."""

    def __init__(self,
                 bot: commands.Bot = None,
                 database: databasecontrol.Database = None,
                 ):
        super().__init__()
        self.database = database
        self.bot = bot

        self.channels = None
        self.setup_items()

    def setup_items(self):
        if self.channels:
            self.add_item(SelectCreatorMenu(self.bot, self.database, self.channels))

        create_button = discord.ui.Button(
            label="Create new Creator",
            style=discord.ButtonStyle.success
        )
        create_button.callback = self.create_button_callback
        self.add_item(create_button)

        if config['website']:
            website_button = discord.ui.Button(
                label="Website",
                url=config['website'],
                style=discord.ButtonStyle.link
            )
            self.add_item(website_button)

    async def send_message(self, interaction: discord.Interaction, edit: bool = False):
        # Create menu with channel hubs
        channel_ids = self.database.get_temp_channel_hubs(interaction.guild.id)
        self.channels = [channel for channel_id in channel_ids if
                         (channel := self.bot.get_channel(channel_id)) is not None]
        self.clear_items()
        self.setup_items()

        embed = discord.Embed(
            title="Setup or Modify Channel Creators",
            description="Customise your channel creators to your specific need.",
            color=0x00ff00
        )
        if not self.channels:
            embed.add_field(
                name="No Current Creators",
                value="There are no channel creators set up.",
                inline=False
            )
        else:
            embed.add_field(
                name="Current Creators:",
                value="",
                inline=False
            )
        for i, channel in enumerate(self.channels):
            child_name = self.database.get_child_name(channel.id)
            user_limit = self.database.get_user_limit(channel.id)
            if user_limit == 0:
                user_limit = "Unlimited"
            embed.add_field(
                name=f"#{i + 1}. {channel.mention}",
                value=f"Child Channel Names: `{child_name}`\nUser Limit: `{user_limit}`\n",
                inline=False
            )

        if edit:
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message(embed=embed, view=self, ephemeral=True)

    async def create_button_callback(self, interaction: discord.Interaction):
        """Callback for the 'Create new Creator' button."""
        modal = CreateCreatorModal(self.bot, self.database)
        await interaction.response.send_modal(modal)


class SelectCreatorMenu(Select):
    """A dropdown menu for selecting a channel creator to edit."""

    def __init__(self,
                 bot: commands.Bot,
                 database: databasecontrol.Database,
                 channels: List[discord.TextChannel],
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
            await interaction.response.send_message("Error: No creators available for select menu.", ephemeral=True, delete_after=10)
            return

        selected_channel_id = int(self.values[0])
        selected_channel = self.bot.get_channel(selected_channel_id)

        await EditCreatorView(self.bot, self.database, selected_channel).send_message(interaction)


class CreateCreatorModal(discord.ui.Modal, title="Create New Creator Channel"):
    def __init__(self, bot: commands.Bot, database: databasecontrol.Database):
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
        try:
            channel = await interaction.guild.create_voice_channel(name="➕ Create Channel")
        except discord.Forbidden:
            await handle_bot_permission_error("manage_channels", interaction)
            return
        except Exception as e:
            await handle_global_error("on_creator_modal_submit", e)
            return
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
        await EditCreatorView(self.bot, self.database, channel).send_message(interaction)

        # Send notification to support server
        if self.bot.user.id == 853490879753617458:
            notification_channel = self.bot.get_channel(int(config["sync_channel_id"]))
        else:
            notification_channel = self.bot.get_channel(int(config["testing_sync_channel_id"]))
        if notification_channel is not None:
            embed = discord.Embed(
                title=f"New Channel Creator!",
                description=f"",
                color=discord.Color.blue()
            )
            embed.add_field(name="Children Names", value=f"{temp_child_name}", inline=True)
            embed.add_field(name="Children User Limit", value=f"{user_limit}", inline=True)
            embed.add_field(name="Creator ID", value=f"{channel.id}", inline=True)
            embed.add_field(name="User", value=f"{interaction.user.name} ({interaction.user.id})", inline=True)
            embed.add_field(name="Guild", value=f"{interaction.guild.name} ({interaction.guild.id})", inline=True)
            is_owner = interaction.channel.guild.owner_id == interaction.user.id
            embed.add_field(name="Is User Server Owner", value=is_owner, inline=True)

            await notification_channel.send(embed=embed)


class EditCreatorView(View):
    """A view containing buttons and menus for managing channel creators."""

    def __init__(self,
                 bot: commands.Bot = None,
                 database: databasecontrol.Database = None,
                 selected_channel: discord.TextChannel = None
                 ):
        super().__init__()
        self.database = database
        self.bot = bot
        self.selected_channel = selected_channel

        delete_button = discord.ui.Button(
            label="Delete",
            style=discord.ButtonStyle.danger
        )
        delete_button.callback = self.delete_creator_button_callback
        self.add_item(delete_button)

        modify_button = discord.ui.Button(
            label="Modify",
            style=discord.ButtonStyle.success
        )
        modify_button.callback = self.modify_button_callback
        self.add_item(modify_button)

        back_button = discord.ui.Button(
            label="Back",
            style=discord.ButtonStyle.secondary
        )
        back_button.callback = self.back_button_callback
        self.add_item(back_button)

    async def send_message(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"#{self.selected_channel.name}",
            description="",
            color=0x00ff00
        )
        embed.add_field(name="Name", value=self.selected_channel.name, inline=True)
        embed.add_field(name="Mention", value=self.selected_channel.mention, inline=True)
        embed.add_field(name="ID", value=str(self.selected_channel.id), inline=True)
        category = f"<#{self.selected_channel.category_id}>" if self.selected_channel.category_id else "None"
        embed.add_field(name="Category", value=category, inline=True)
        child_name = self.database.get_child_name(self.selected_channel.id)
        embed.add_field(name="Child Names", value=child_name, inline=True)
        user_limit = self.database.get_user_limit(self.selected_channel.id)
        if user_limit == 0:
            user_limit = "Unlimited"
        embed.add_field(name="User Limit", value=user_limit, inline=True)

        await interaction.response.edit_message(embed=embed, view=self)

    async def back_button_callback(self, interaction: discord.Interaction):
        """Callback for the 'Back' button."""
        # Create an embed with options
        await SelectCreatorView(self.bot, self.database).send_message(interaction, edit=True)

    async def modify_button_callback(self, interaction: discord.Interaction):
        """Callback for the 'Modify existing creators' button."""
        modal = EditCreatorModal(self.bot, self.database, self.selected_channel)
        await interaction.response.send_modal(modal)

    async def delete_creator_button_callback(self, interaction: discord.Interaction):
        """Callback for the 'Delete creator' button."""

        # Deletes channel from discord before deleting from db
        guild_id = self.selected_channel.guild.id
        channel_id = self.selected_channel.id
        try:
            await self.selected_channel.delete()
        except discord.Forbidden:
            await handle_bot_permission_error("manage_channels", interaction)
            return
        except Exception as e:
            await handle_global_error("on_voice_state_update", e)
            return
        self.database.delete_temp_channel_hub(guild_id, channel_id)

        # Create an embed with options
        await SelectCreatorView(self.bot, self.database).send_message(interaction, edit=True)


class EditCreatorModal(discord.ui.Modal, title="Edit Creator Channel"):
    def __init__(self, bot: commands.Bot, database: databasecontrol.Database, selected_channel):
        super().__init__()
        self.bot = bot
        self.database = database
        self.selected_channel = selected_channel

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
        max_length=2
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

        self.database.delete_temp_channel_hub(interaction.guild.id, self.selected_channel.id)
        self.database.add_temp_channel_hub(interaction.guild.id, self.selected_channel.id, temp_child_name, user_limit)

        # Create an embed with channel information
        await EditCreatorView(self.bot, self.database, self.selected_channel).send_message(interaction)


class TempChannelsCog(commands.Cog):
    """A cog that manages temporary voice channels."""

    def __init__(self, bot: commands.Bot, database):
        self.bot = bot
        self.database = database

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Listener to handle deletion of channel hubs."""
        try:
            self.database.delete_temp_channel_hub(channel.guild.id, channel.id)
        except Exception as error:
            print(f"Error in on_guild_channel_delete: {error}")
            await handle_global_error("on_guild_channel_delete")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Listener to handle creation and deletion of temporary channels."""
        try:
            tasks = []
            left_channel = before.channel
            joined_channel = after.channel

            # Handle channel deletion if user left a channel
            if left_channel:
                # Filter for temporary channels
                if self.database.is_temp_channel(left_channel.id):
                    # If the channel is empty, delete the channel
                    if len(left_channel.members) == 0:
                        tasks.append(self.delete_channel_async(left_channel, member, before.channel))
                        self.database.delete_temp_channel(before.channel.id)
                    # If owner leaves the channel, set owner to None
                    elif self.database.get_owner_id(left_channel.id) == member.id and (not joined_channel or joined_channel.id != left_channel.id):
                        self.database.set_owner_id(left_channel.id, None)
                        await cogs.tempchannels.control.update_info_embed(self.database, left_channel)

            # Handle channel creation if user joined a hub channel
            if joined_channel:
                print(f"After voice update for '{member.name}' in '{joined_channel.name}' in '{member.guild.name}'")
                channel_hub_ids = self.database.get_temp_channel_hubs(member.guild.id)
                if joined_channel.id in channel_hub_ids:
                    # Prepare data for channel creation
                    child_name_template = self.database.get_child_name(joined_channel.id)
                    existing_numbers = set(self.database.get_temp_channel_numbers(member.guild.id, joined_channel.id))

                    # Find the next available channel number
                    count = 1
                    while count in existing_numbers:
                        count += 1

                    # Format the child channel name
                    formatted_child_name = child_name_template.format(count=count, user=member.display_name)
                    user_limit = self.database.get_user_limit(joined_channel.id) or 0

                    try:
                        # Start creating the channel asynchronously
                        overwrites = {
                            member.guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True, send_messages=True),
                        }
                        create_channel_task = asyncio.create_task(
                            member.guild.create_voice_channel(
                                name=formatted_child_name,
                                category=joined_channel.category,
                                user_limit=user_limit,
                                overwrites=overwrites,
                            )
                        )

                        # While the channel is being created, run other independent tasks
                        if tasks:
                            await asyncio.gather(*tasks)
                            tasks = []  # Reset tasks list after running them

                        # Wait for the channel to be created
                        channel = await create_channel_task

                        # Add the new channel to the database
                        self.database.add_temp_channel(
                            member.guild.id, channel.id, joined_channel.id, member.id, count
                        )

                        # Move the user to the new channel
                        await member.move_to(channel)

                        # Schedule sending the control view message concurrently
                        await self.send_control_view_async(channel)

                    except discord.Forbidden:
                        # How do i know what permission was forbidden?
                        await handle_bot_permission_error("manage_channels", user=member, channel=joined_channel)
                        return
                    except Exception as e:
                        await handle_global_error("on_voice_state_update", e)
                        return

            # Run any remaining tasks concurrently
            if tasks:
                await asyncio.gather(*tasks)

        except Exception as error:
            print(f"Error in on_voice_state_update: {error}")
            await handle_global_error("on_voice_state_update", error)

    async def delete_channel_async(self, channel, member, before_channel):
        try:
            await channel.delete()
        except discord.Forbidden:
            await handle_bot_permission_error("manage_channels", user=member, channel=before_channel)
        except Exception as e:
            await handle_global_error("delete_channel_async", e)

    async def send_control_view_async(self, channel):
        try:
            ControlView = cogs.tempchannels.control.CreateControlView(self.bot, self.database, channel)
            await ControlView.send_initial_message()
        except discord.Forbidden:
            await handle_bot_permission_error("manage_channels", user=None, channel=channel)
        except Exception as e:
            await handle_global_error("send_control_view_async", e)

    @discord.app_commands.command(
        name="setup_creators",
        description="Create and edit Channel Hubs."
    )
    @discord.app_commands.checks.has_permissions(manage_channels=True)
    async def setup_creators(self, interaction: discord.Interaction):
        """Command to set up channel creators."""
        try:
            # Create an embed with options
            await SelectCreatorView(self.bot, self.database).send_message(interaction)
        except Exception as error:
            await handle_command_error(interaction, error)

    @setup_creators.error
    async def setup_creators_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await handle_user_permission_error("manage_channels", interaction)
        else:
            await handle_command_error(interaction, error)

    def cog_unload(self):
        """Cleanup when the cog is unloaded."""
        self.database.close()


async def setup(bot: commands.Bot, database):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(TempChannelsCog(bot, database))
