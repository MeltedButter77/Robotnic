import asyncio
from discord import app_commands
from discord.ext import tasks
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
        label="NAME (Variables: {user}, {count}, {activity})",
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
            try:
                user_limit = int(user_limit)
            except ValueError:
                user_limit = 0
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
        embed.add_field(name="Mention/Link", value=self.selected_channel.mention, inline=True)
        embed.add_field(name="ID", value=str(self.selected_channel.id), inline=True)

        category = f"<#{self.selected_channel.category_id}>" if self.selected_channel.category_id else "None"
        embed.add_field(name="Category", value=category, inline=False)

        child_name = self.database.get_child_name(self.selected_channel.id)
        embed.add_field(name="Child Names", value=child_name, inline=True)

        user_limit = self.database.get_user_limit(self.selected_channel.id)
        embed.add_field(name="Child User Limit", value="Unlimited" if user_limit == 0 else user_limit, inline=True)

        child_category_id = self.database.get_child_category_id(self.selected_channel.id)
        category_name = "Parent Category" if child_category_id == 0 else self.selected_channel.guild.get_channel(child_category_id).name
        embed.add_field(name="Child Category", value=category_name, inline=True)

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

        def truncate(text, max_length=25):
            return text if len(text) <= max_length else text[:max_length] + "..."

        child_name_placeholder = truncate(f"Current: {self.database.get_child_name(self.selected_channel.id)}")
        user_limit_placeholder = truncate(f"Current: {self.database.get_user_limit(self.selected_channel.id)}")
        child_category_placeholder = truncate(f"Current: {self.database.get_child_category_id(self.selected_channel.id)}")

        # Define the text inputs
        self.input_child_name = discord.ui.TextInput(
            label="NAME (Variables: {user}, {count}, {activity})",
            placeholder=child_name_placeholder,
            required=False,
            max_length=25
        )
        self.input_user_limit = discord.ui.TextInput(
            label="User Limit (Unlimited = 0)",
            placeholder=user_limit_placeholder,
            required=False,
            max_length=2
        )
        self.input_child_category = discord.ui.TextInput(
            label="Child Category ID (Under creator = 0)",
            placeholder=child_category_placeholder,
            required=False,
            max_length=25
        )

        self.add_item(self.input_child_name)
        self.add_item(self.input_user_limit)
        self.add_item(self.input_child_category)

    async def on_submit(self, interaction: discord.Interaction):
        current_temp_child_name = self.database.get_child_name(self.selected_channel.id)
        current_user_limit = self.database.get_user_limit(self.selected_channel.id)
        current_child_category = self.database.get_child_category_id(self.selected_channel.id)

        # Create a new voice channel and add it to the database
        temp_child_name = str(self.input_child_name.value) if self.input_child_name.value else str(current_temp_child_name)
        user_limit = self.input_user_limit.value if self.input_user_limit.value else current_user_limit
        child_category_id = self.input_child_category.value if self.input_child_category.value else current_child_category

        try:
            user_limit = int(user_limit)
        except ValueError:
            user_limit = current_user_limit
        try:
            child_category_id = int(child_category_id)
        except ValueError:
            child_category_id = child_category_id

        # Update database
        self.database.delete_temp_channel_hub(interaction.guild.id, self.selected_channel.id)
        self.database.add_temp_channel_hub(interaction.guild.id, self.selected_channel.id, temp_child_name, user_limit, child_category_id)

        # Create an embed with channel information
        await EditCreatorView(self.bot, self.database, self.selected_channel).send_message(interaction)


class TempChannelsCog(commands.Cog):
    """A cog that manages temporary voice channels."""

    def __init__(self, bot: commands.Bot, database):
        self.bot = bot
        self.database = database
        self.update_channels_name.start()  # Start the loop when the cog is loaded

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
            ### Order of operations here is important as we want creation to be the fastest, then deletion, then updating

            # Handle channel creation if user joined a hub channel
            if after.channel:
                await self.create_channel_async(after.channel, member)

            # Handle channel deletion if user left a channel
            if before.channel:
                await self.delete_channel_async(before.channel, after.channel, member)

        except Exception as error:
            print(f"Error in on_voice_state_update: {error}")
            await handle_global_error("on_voice_state_update", error)

    async def create_channel_async(self, joined_channel, member):
        channel_hub_ids = self.database.get_temp_channel_hubs(member.guild.id)
        if joined_channel.id in channel_hub_ids:
            try:
                # Create the channel with an initial name (hourglass emoji)
                overwrites = {
                    member.guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True, send_messages=True, connect=True),
                }
                channel = await member.guild.create_voice_channel(
                    name="⏳",
                    category=joined_channel.guild.get_channel(self.database.get_child_category_id(joined_channel.id)) or joined_channel.category,
                    user_limit=self.database.get_user_limit(joined_channel.id) or 0,
                    position=joined_channel.position,
                    overwrites=overwrites,
                )

                # Move the user to the new channel as quickly as possible
                try:
                    await member.move_to(channel)
                except discord.Forbidden:
                    await handle_bot_permission_error("move_to", member)
                    await channel.delete()
                except Exception as e:
                    await channel.delete()
                    return

                # Add the new channel to the database immediately
                count = 1
                existing_numbers = set(self.database.get_temp_channel_numbers(member.guild.id, joined_channel.id))
                while count in existing_numbers:
                    count += 1

                self.database.add_temp_channel(
                    member.guild.id, channel.id, joined_channel.id, member.id, count
                )

                # Prepare the proper activity name and formatted name for the channel
                activities = []
                for member in channel.members:
                    for activity in member.activities:
                        if activity.type == discord.ActivityType.playing:
                            if activity.name.lower() not in (name.lower() for name in activities):
                                activities.append(activity.name)
                if len(activities) <= 0:
                    activities.append("General")
                activities.sort(key=len)
                activity_name = ", ".join(activities)

                child_name_template = self.database.get_child_name(joined_channel.id)
                formatted_child_name = child_name_template.format(count=count, user=member.display_name, activity=activity_name)
                if len(formatted_child_name) > 100:
                    formatted_child_name = formatted_child_name[:97] + "..."

                # Update the channel name after user is in
                await channel.edit(name=formatted_child_name)

                # Refetch the channel to ensure updated data
                channel = await channel.guild.fetch_channel(channel.id)

                # Schedule sending the control view message concurrently
                await self.send_control_view_async(channel)

                print(f"'{member.display_name}' has joined '{joined_channel.name}' in '{member.guild.name}' with the name template of '{child_name_template}'. Created '{channel.name}'.")

            except discord.Forbidden:
                await handle_bot_permission_error("manage_channels, view_channels, connect", user=member, channel=joined_channel)
                return
            except Exception as e:
                await handle_global_error("on_voice_state_update", e)
                return

    # Updates count, owner & activity for every temp_channel
    @tasks.loop(minutes=2)
    async def update_channels_name(self):
        channels = self.database.get_temp_notrenamed_channels()
        print(f"Updating names of {len(channels)} temp channels {[self.bot.get_channel(channel_id) for channel_id in channels]}")

        if len(channels) <= 0:
            return

        for channel_id in channels:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue
            hub_id = self.database.get_temp_channel_creator_id(channel_id)

            # template has {count}, {activity} and {user} which are filled below
            child_name_template = self.database.get_child_name(hub_id)

            if "{user}" not in child_name_template and "{activity}" not in child_name_template:
                continue

            count = self.database.get_temp_channel_number(channel.id)

            activities = []
            for member in channel.members:
                for activity in member.activities:
                    if activity.type == discord.ActivityType.playing:
                        if activity.name.lower() not in (name.lower() for name in activities):
                            activities.append(activity.name)
            if len(activities) <= 0:
                activities.append("General")
            activities.sort(key=len)
            activity_name = ", ".join(activities)

            channel_owner_id = self.database.get_owner_id(channel.id)
            channel_owner = self.bot.get_user(channel_owner_id)
            channel_owner_display_name = "Noone"
            if channel_owner:
                channel_owner_display_name = channel_owner.display_name

            # Format the child channel name
            formatted_child_name = child_name_template.format(count=count, user=channel_owner_display_name, activity=activity_name)
            if len(formatted_child_name) > 100:
                formatted_child_name = formatted_child_name[:97] + "..."

            # rename channel now that the name is formatted
            if formatted_child_name != channel.name:
                try:
                    await channel.edit(name=str(formatted_child_name))

                    # Re-fetch the channel to ensure updated data for updating info embed
                    channel = await channel.guild.fetch_channel(channel.id)

                    await cogs.tempchannels.control.update_info_embed(self.database, channel)
                except discord.Forbidden:
                    await handle_bot_permission_error("manage_channels", user=channel_owner, channel=channel)
                except Exception as e:
                    await handle_global_error("on_voice_state_update", e)

    async def delete_channel_async(self, left_channel, joined_channel, member):
        # Filter for temporary channels
        if self.database.is_temp_channel(left_channel.id):
            # If the channel is empty, delete the channel
            if len(left_channel.members) == 0:
                try:
                    await left_channel.delete()
                except discord.Forbidden:
                    await handle_bot_permission_error("manage_channels", channel=left_channel)
                except Exception as e:
                    await handle_global_error("delete_channel_async", e)
                self.database.delete_temp_channel(left_channel.id)
            # If owner leaves the channel, set owner to None
            elif self.database.get_owner_id(left_channel.id) == member.id and (not joined_channel or joined_channel.id != left_channel.id):
                self.database.set_owner_id(left_channel.id, None)
                await cogs.tempchannels.control.update_info_embed(self.database, left_channel)

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
