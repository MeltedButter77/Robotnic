import json
import os
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View
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


async def create_control_menu(bot: commands.Bot, database: databasecontrol.Database, channel: discord.TextChannel, last_followup_message_id=None):
    view = CreateControlView(
        database=database,
        bot=bot,
        channel=channel,
        last_followup_message_id=last_followup_message_id,
    )

    embed = discord.Embed(
        title="Manage your Temporary Channel",
        description="",
        color=0x00ff00
    )
    # embed.add_field(
    #     name="Field Name",
    #     value="Field Value.",
    #     inline=False
    # )
    return view, embed


class CreateControlView(View):
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
            text = "Your channel is now public."
        elif new_state == ChannelState.LOCKED:
            permissions = {'connect': False, 'view_channel': True}
            text = "Your channel is now locked."
        elif new_state == ChannelState.HIDDEN:
            permissions = {'view_channel': False}
            text = "Your channel is now hidden."
        else:
            await error_handling.handle_global_error("Unexpected channel state")
            return

        await interaction.channel.set_permissions(interaction.guild.default_role, **permissions)
        self.database.update_channel_state(interaction.channel.guild.id, interaction.channel.id, new_state.value)

        if self.last_followup_message_id:
            try:
                followup_message = await interaction.channel.fetch_message(self.last_followup_message_id)
                await followup_message.edit(content=text)
            except discord.NotFound:
                followup_message = await interaction.followup.send(text)
        else:
            followup_message = await interaction.followup.send(text)

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
