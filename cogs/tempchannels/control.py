import time
import asyncio
from logging import disable
from discord import app_commands
import databasecontrol
from error_handling import handle_bot_permission_error, handle_command_error, handle_global_error, \
    handle_user_permission_error
import json
import os
import discord
from discord.ext import commands
from discord.ui import Select, View

base_directory = os.getenv('BASE_DIR', os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(base_directory, 'config.json')
# Load the configuration from config.json
with open(config_path) as config_file:
    config = json.load(config_file)


async def create_control_menu(bot: commands.Bot, database: databasecontrol.Database, channel: discord.TextChannel, last_followup_message=None):
    view = CreateControlView(
        database=database,
        bot=bot,
        channel=channel,
        last_followup_message=last_followup_message,
    )

    embed = discord.Embed(
        title="Title",
        description="Description.",
        color=0x00ff00
    )
    embed.add_field(
        name="Field Name",
        value="Field Value.",
        inline=False
    )
    return view, embed


class CreateControlView(View):
    """A view containing buttons and menus for managing channel creators."""

    def __init__(self, database, bot: commands.Bot, channel, last_followup_message):
        super().__init__()
        self.bot = bot
        self.database = database
        self.last_followup_message = last_followup_message

        # 0 = public, 1 = locked, 2 = hidden
        channel_state = self.database.get_channel_state(channel.guild.id, channel.id)

        if channel_state != 1:
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

        if channel_state != 2:
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

        if channel_state != 0:
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

    async def lock_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            connect=False,
            view_channel=True
        )

        self.database.update_channel_state(
            guild_id=interaction.channel.guild.id,
            channel_id=interaction.channel.id,
            new_state=1
        )

        if self.last_followup_message:
            try:
                await self.last_followup_message.delete()
            except discord.NotFound:
                pass  # Message was already deleted
        new_followup_message = await interaction.followup.send(f"Locked", ephemeral=True)

        view, embed = await create_control_menu(self.bot, self.database, interaction.channel, new_followup_message)
        await interaction.message.edit(embed=embed, view=view)

    async def hide_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            view_channel=False
        )

        self.database.update_channel_state(
            guild_id=interaction.channel.guild.id,
            channel_id=interaction.channel.id,
            new_state=2
        )

        if self.last_followup_message:
            try:
                await self.last_followup_message.delete()
            except discord.NotFound:
                pass  # Message was already deleted
        new_followup_message = await interaction.followup.send(f"Hidden", ephemeral=True)

        view, embed = await create_control_menu(self.bot, self.database, interaction.channel, new_followup_message)
        await interaction.message.edit(embed=embed, view=view)

    async def public_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            connect=True,
            view_channel=True
        )

        self.database.update_channel_state(
            guild_id=interaction.channel.guild.id,
            channel_id=interaction.channel.id,
            new_state=0
        )

        if self.last_followup_message:
            try:
                await self.last_followup_message.delete()
            except discord.NotFound:
                pass  # Message was already deleted
        new_followup_message = await interaction.followup.send(f"Global", ephemeral=True)

        view, embed = await create_control_menu(self.bot, self.database, interaction.channel, new_followup_message)
        await interaction.message.edit(embed=embed, view=view)


class ControlTempChannelsCog(commands.Cog):
    def __init__(self, bot: commands.Bot, database):
        self.bot = bot
        self.database = database
        self.last_followup_message = None

    @discord.app_commands.command(name="control", description="Control your temp channel")
    @discord.app_commands.checks.has_permissions(manage_channels=True)
    async def control(self, interaction: discord.Interaction):
        try:
            # Create an embed with options
            view, embed = await create_control_menu(self.bot, self.database, temp_channel)
            await interaction.channel.send(embed=embed, view=view)
        except Exception as error:
            await handle_command_error(interaction, error)

    @control.error
    async def control_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await handle_user_permission_error("manage_channels", interaction)
        else:
            await handle_command_error(interaction, error)


async def setup(bot: commands.Bot, database):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(ControlTempChannelsCog(bot, database))
