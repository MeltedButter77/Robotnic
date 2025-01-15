from dataclasses import fields

import discord
import traceback
from discord.ext import commands
import json
import os

# Load the configuration from config.json
base_directory = os.getenv('BASE_DIR', os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(base_directory, 'config.json')
# Load the configuration from config.json
with open(config_path) as config_file:
    config = json.load(config_file)


async def handle_user_permission_error(permission: str, interaction=None, user=None, channel: discord.abc.GuildChannel = None):
    """Handles permission errors for command interactions."""
    if interaction:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

    embed = discord.Embed(
        title="Not enough permissions",
        description=f"You do not have the required permissions to use this command. If you believe this is an error, please report this issue below.",
        color=discord.Color.red()
    )
    embed.add_field(
        name="Required Permissions:",
        value=f"`{permission}`",
        inline=False
    )
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(style=discord.ButtonStyle.url, label="Report an issue", url=f"{config['support_server']}"))

    if interaction:
        await interaction.followup.send(
            f"Sorry {interaction.user.mention}, You need more permissions.",
            embed=embed,
            view=view,
            ephemeral=True
        )
    else:
        await channel.send(
            f"Sorry {user.mention}, You need more permissions.",
            embed=embed,
            view=view,
        )


async def handle_channel_owner_error(interaction=None, user=None, channel: discord.abc.GuildChannel = None):
    """Handles permission errors for command interactions."""
    if interaction:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

    embed = discord.Embed(
        title="You are not the Owner of this channel",
        description=f"If you believe this is an error, please report this issue below.",
        color=discord.Color.red()
    )
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(style=discord.ButtonStyle.url, label="Report an issue", url=f"{config['support_server']}"))

    if interaction:
        await interaction.followup.send(
            f"Sorry {interaction.user.mention}, This is not your channel.",
            embed=embed,
            view=view,
            ephemeral=True
        )
    else:
        await channel.send(
            f"Sorry {user.mention}, You need more permissions.",
            embed=embed,
            view=view,
        )


async def handle_bot_permission_error(permission: str, interaction=None, user=None, channel: discord.abc.GuildChannel = None):
    """Handles permission errors for command interactions."""
    if interaction:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

    embed = discord.Embed(
        title="Bot Permission Error",
        description=f"Please ensure i have access to the following permissions in any category you would like a creator channel in.",
        color=discord.Color.red()
    )
    embed.add_field(
        name="Required Permissions:",
        value=f"`{permission}`",
        inline=False
    )
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(style=discord.ButtonStyle.url, label="Report an issue", url=f"{config['support_server']}"))

    if interaction:
        await interaction.followup.send(
            f"Sorry {interaction.user.mention}, I need more permissions.",
            embed=embed,
            view=view,
            ephemeral=True
        )
    else:
        await channel.send(
            f"Sorry {user.mention}, I need more permissions.",
            embed=embed,
            view=view,
        )


async def handle_command_error(interaction: discord.Interaction, error: Exception):
    """Handles errors for command interactions."""
    embed = discord.Embed(
        title="Error Information",
        description=f"{error}",
        color=discord.Color.red()
    )
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(style=discord.ButtonStyle.url, label="Report an issue", url=f"{config['support_server']}"))

    await interaction.response.send_message(
        f"Sorry, it seems you have run into an error. Please report it in the discord server.",
        embed=embed,
        view=view,
        ephemeral=True
    )


async def handle_global_error(event_method: str, *args, **kwargs):
    """Handles global errors outside of command interactions."""
    embed = discord.Embed(
        title="Unexpected Error",
        description=f"An error occurred during the event `{event_method}`.",
        color=discord.Color.red()
    )

    # Log the error to the console
    error_info = traceback.format_exc()
    print(f"Error in event `{event_method}`:\n{error_info}")

    try:
        if args and isinstance(args[0], discord.Interaction):
            interaction = args[0]
            view = discord.ui.View()
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="Report an issue",
                                            url=f"{config['support_server']}"))

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Sorry, an unexpected error occurred. Please report it in the Discord server.",
                    embed=embed,
                    ephemeral=True,
                    view=view
                )
            else:
                await interaction.followup.send(
                    "Sorry, an unexpected error occurred.",
                    embed=embed,
                    ephemeral=True,
                    view=view
                )
        elif args and isinstance(args[0], commands.Context):
            ctx = args[0]
            view = discord.ui.View()
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="Report an issue",
                                            url=f"{config['support_server']}"))
            await ctx.send(
                "Sorry, an unexpected error occurred. Please report it in the Discord server.",
                embed=embed,
                view=view
            )
    except Exception as e:
        # Log any exception that occurs while handling the error
        print(f"Failed to send error report: {e}")
