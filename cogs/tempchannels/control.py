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


async def create_followup_menu(bot: commands.Bot, database: databasecontrol.Database, interaction: discord.Interaction, followup_id=None):
    """Updates the follow-up message in the channel."""
    channel_state = ChannelState(database.get_channel_state(interaction.channel.guild.id, interaction.channel.id))

    view = CreateFollowupView(
        bot=bot,
        database=database,
        channel=interaction.channel,
        channel_state=channel_state,
        followup_id=followup_id
    )

    # Separate members who can and can't connect
    can_connect = []
    cant_connect = []
    if interaction.channel.type == discord.ChannelType.voice:
        for member in interaction.channel.guild.members:
            if not member.bot:
                permissions = interaction.channel.permissions_for(member)
                if permissions.connect:
                    can_connect.append(member)
                else:
                    cant_connect.append(member)

    # Create the embed message
    embed = discord.Embed(
        title=interaction.channel.name,
        color=0x00ff00
    )
    embed.add_field(
        name="Allowed Users",
        value=", ".join([member.mention for member in can_connect]) or "None",
        inline=True
    )
    embed.add_field(
        name="Blocked Users",
        value=", ".join([member.mention for member in cant_connect]) or "None",
        inline=True
    )

    # Determine the channel state
    channel_states = {
        ChannelState.PUBLIC: "Public",
        ChannelState.LOCKED: "Locked",
        ChannelState.HIDDEN: "Hidden"
    }
    text = channel_states.get(channel_state, "Unknown")

    return text, view, embed


class CreateFollowupView(discord.ui.View):
    """A view containing buttons and menus for managing channel creators."""

    def __init__(self, bot: commands.Bot, database: databasecontrol.Database, channel, channel_state, followup_id=0):
        super().__init__(timeout=None)
        self.bot = bot
        self.database = database
        self.channel = channel
        self.channel_state = channel_state

        if channel_state == ChannelState.PUBLIC:
            ban_perms = {'connect': False, 'view_channel': False}
            self.add_item(UpdatePermSelectMenu(bot, self.database, ban_perms, "Select a user or role to BAN"))
            # TODO: Need a remove from banlist mechanism
        elif channel_state == ChannelState.LOCKED or channel_state == ChannelState.HIDDEN:
            allow_perms = {'connect': True, 'view_channel': True}
            self.add_item(UpdatePermSelectMenu(bot, self.database, allow_perms, "Select a user or role to ALLOW"))
            # TODO: Need a remove from allowlist mechanism


class UpdatePermSelectMenu(discord.ui.MentionableSelect):
    """A dropdown menu for selecting users or roles to give view and connect permissions to."""

    def __init__(self,
                 bot: commands.Bot,
                 database: databasecontrol.Database,
                 permissions: dict,
                 placeholder: str
                 ):
        self.bot = bot
        self.database = database
        self.permissions = permissions

        if permissions['connect']:
            super().__init__(
                placeholder=placeholder,
                min_values=1,
                max_values=25
            )
        else:
            super().__init__(
                placeholder="Select a user or role to BLOCK",
                min_values=1,
                max_values=25
            )

    async def callback(self, interaction: discord.Interaction):
        """Handle the selection of users or roles."""
        selected_entities = self.values  # The selected users or roles

        # Iterate through the selected users or roles
        for entity in selected_entities:
            # Check if the entity is a Member (user) or a Role
            member = interaction.guild.get_member(int(entity.id))
            if member:
                target = member
            else:
                # Fetch all roles and find the matching role by ID
                roles = await interaction.guild.fetch_roles()
                target = discord.utils.get(roles, id=int(entity.id))

            if target:
                # Update permissions for viewing and connecting
                await self.channel.set_permissions(
                    target,
                    **self.permissions
                )

        text, view, embed = await create_followup_menu(self.bot, self.database, interaction)

        await interaction.response.edit_message(content="updated", embed=embed, view=view)


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

        # update the control menu with wrong followup message. this gets a response to the user quicker but may break when spammed
        view, embed = await create_control_menu(self.bot, self.database, interaction.channel,
                                                self.last_followup_message_id)
        await interaction.message.edit(embed=embed, view=view)

        # Create or update followup message
        text, view, embed = await create_followup_menu(self.bot, self.database, interaction)

        # Try to fetch the last follow-up message, if exists
        followup_message = None
        if self.last_followup_message_id:
            try:
                followup_message = await interaction.channel.fetch_message(self.last_followup_message_id)
            except discord.NotFound:
                followup_message = None
        # Edit the followup message if it exists, otherwise send a new follow-up
        if followup_message:
            await followup_message.edit(content=text, view=view, embed=embed)
        else:
            followup_message = await interaction.followup.send(content=text, view=view, embed=embed)

        # update the control menu with correct followup message
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
