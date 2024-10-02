import json
import os
import time

import discord
from discord import app_commands
from discord.ext import commands
import discord.ui
import databasecontrol
import error_handling
from enum import Enum

base_directory = os.getenv('BASE_DIR', os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(base_directory, 'config.json')
# Load the configuration from config.json
with open(config_path) as config_file:
    config = json.load(config_file)


class ChannelState(Enum):
    PUBLIC = 0
    LOCKED = 1
    HIDDEN = 2


async def create_followup_menu(bot: commands.Bot, channel: discord.TextChannel, channel_state):
    view = CreateFollowupView(
        bot=bot,
        channel=channel,
        channel_state=channel_state,
    )

    # Get members that can view and connect
    can_view_channel = []
    can_connect = []

    # Iterate through all members in the guild
    for member in channel.guild.members:
        # Check if the member can view the channel
        if channel.permissions_for(member).view_channel:
            can_view_channel.append(member)

        # Check if the member can connect (for voice channels)
        if channel.type == discord.ChannelType.voice and channel.permissions_for(member).connect:
            can_connect.append(member)

    embed = discord.Embed(
        title=f"{channel.name}",
        description = f"",
        color=0x00ff00,
    )
    embed.add_field(
        name="Users who can join",
        value=f"{', '.join([member.mention for member in can_connect])}",
        inline=True
    )

    text = ""
    if channel_state == ChannelState.PUBLIC:
        text = "Public"
    elif channel_state == ChannelState.LOCKED:
        text = "Locked"
    elif channel_state == ChannelState.HIDDEN:
        text = "Hidden"

    return view, embed, text


class CreateFollowupView(discord.ui.View):
    """A view containing buttons and menus for managing channel creators."""

    def __init__(self, bot: commands.Bot, channel, channel_state):
        super().__init__(timeout=None)
        self.bot = bot
        self.channel = channel
        self.channel_state = channel_state

        button = discord.ui.Button(
            label="button",
            style=discord.ButtonStyle.primary
        )
        button.callback = self.button_callback

        self.add_item(PermissionSelectMenu(bot=bot, channel=channel, channel_state=channel_state))

        self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        print("clicked followup button")


class PermissionSelectMenu(discord.ui.MentionableSelect):
    """A dropdown menu for selecting a users or roles to give view and connect permissions to."""

    def __init__(self,
                bot: commands.Bot,
                channel: discord.TextChannel,
                channel_state = None,
            ):
        self.bot = bot
        self.channel = channel
        self.channel_state = channel_state

        super().__init__(
            placeholder="Select a user or role",
            min_values=1,
            max_values=25
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle the selection of a channel creator."""
        pass


async def create_control_menu(bot: commands.Bot, database: databasecontrol.Database, channel: discord.TextChannel, last_followup_message_id=None):
    view = CreateControlView(
        database=database,
        bot=bot,
        channel=channel,
        last_followup_message_id=last_followup_message_id,
    )

    embed = discord.Embed(
        title="Manage your Temporary Channel",
        description=f"Use the buttons below to manage your temporary channel.",
        color=0x00ff00
    )
    # embed.add_field(
    #     name="Field Name",
    #     value="Field Value.",
    #     inline=False
    # )
    return view, embed


class CreateControlView(discord.ui.View):
    """A view containing buttons and menus for managing channel creators."""

    def __init__(self, database, bot: commands.Bot, channel, last_followup_message_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.database = database
        self.last_followup_message_id = last_followup_message_id

        channel_state = self.database.get_channel_state(channel.guild.id, channel.id)

        if channel_state != ChannelState.LOCKED.value:
            lock_button = discord.ui.Button(
                label="Lock",
                style=discord.ButtonStyle.primary
            )
        else:
            lock_button = discord.ui.Button(
                label="Lock",
                style=discord.ButtonStyle.primary,
                disabled=True
            )
        lock_button.callback = self.lock_button_callback

        if channel_state != ChannelState.HIDDEN.value:
            hide_button = discord.ui.Button(
                label="Hide",
                style=discord.ButtonStyle.primary
            )
        else:
            hide_button = discord.ui.Button(
                label="Hide",
                style=discord.ButtonStyle.primary,
                disabled=True
            )
        hide_button.callback = self.hide_button_callback

        if channel_state != ChannelState.PUBLIC.value:
            public_button = discord.ui.Button(
                label="Public",
                style=discord.ButtonStyle.primary
            )
        else:
            public_button = discord.ui.Button(
                label="Public",
                style=discord.ButtonStyle.primary,
                disabled=True
            )
        public_button.callback = self.public_button_callback

        self.add_item(public_button)
        self.add_item(hide_button)
        self.add_item(lock_button)

    async def update_channel(self, interaction, new_state: ChannelState):
        await interaction.response.defer()

        owner_id = self.database.get_owner_id(interaction.channel.id)
        if not interaction.user.id == owner_id:
            return await error_handling.handle_channel_owner_error(interaction)

        if new_state == ChannelState.PUBLIC:
            permissions = {'connect': True, 'view_channel': True}
        elif new_state == ChannelState.LOCKED:
            permissions = {'connect': False, 'view_channel': True}
        elif new_state == ChannelState.HIDDEN:
            permissions = {'view_channel': False}
        else:
            await error_handling.handle_global_error("Unexpected channel state")
            return

        # set permissions and channel_state in database
        connected_users = [member for member in interaction.channel.members if not member.bot]
        for user in connected_users:
            await interaction.channel.set_permissions(user, connect=True, view_channel=True)
        await interaction.channel.set_permissions(interaction.guild.default_role, **permissions)
        self.database.update_channel_state(interaction.channel.guild.id, interaction.channel.id, new_state.value)

        # Create the followup message and menu
        view, embed, text = await create_followup_menu(self.bot, interaction.channel, new_state)
        if self.last_followup_message_id:
            try:
                followup_message = await interaction.channel.fetch_message(self.last_followup_message_id)
                await followup_message.edit(content=text, view=view, embed=embed)
            except discord.NotFound:
                followup_message = await interaction.followup.send(content=text, view=view, embed=embed)
        else:
            followup_message = await interaction.followup.send(content=text, view=view, embed=embed)

        view, embed = await create_control_menu(self.bot, self.database, interaction.channel, followup_message.id)
        await interaction.message.edit(embed=embed, view=view)

    async def lock_button_callback(self, interaction: discord.Interaction):
        await self.update_channel(
            interaction,
            ChannelState.LOCKED,
        )

    async def hide_button_callback(self, interaction: discord.Interaction):
        await self.update_channel(
            interaction,
            ChannelState.HIDDEN,
        )

    async def public_button_callback(self, interaction: discord.Interaction):
        await self.update_channel(
            interaction,
            ChannelState.PUBLIC,
        )


class ControlTempChannelsCog(commands.Cog):
    def __init__(self, bot: commands.Bot, database):
        self.bot = bot
        self.database = database
        self.last_followup_message_id = None

    @discord.app_commands.command(name="control", description="Control your temp channel")
    @discord.app_commands.checks.has_permissions(manage_channels=True)
    async def control(self, interaction: discord.Interaction):
        try:
            # Create an embed with options
            view, embed = await create_control_menu(self.bot, self.database, temp_channel)
            await interaction.channel.send(embed=embed, view=view)
        except Exception as error:
            await error_handling.handle_command_error(interaction, error)

    @control.error
    async def control_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await error_handling.handle_user_permission_error("manage_channels", interaction)
        else:
            await error_handling.handle_command_error(interaction, error)


async def setup(bot: commands.Bot, database):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(ControlTempChannelsCog(bot, database))
