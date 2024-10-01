from discord import app_commands
from error_handling import handle_bot_permission_error, handle_command_error, handle_global_error, handle_user_permission_error
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


async def create_control_menu(bot: commands.Bot, interaction: discord.Interaction = None, channel: discord.abc.GuildChannel = None):
    view = CreateControlView(
        bot=bot
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
    if interaction:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    elif channel:
        await channel.send(embed=embed, view=view)


class CreateControlView(View):
    """A view containing buttons and menus for managing channel creators."""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

        button = discord.ui.Button(
            label="lock",
            style=discord.ButtonStyle.success
        )
        button.callback = self.lock_button_callback
        self.add_item(button)

    async def lock_button_callback(self, interaction: discord.Interaction):
        # Defer the response to acknowledge the interaction
        await interaction.response.defer()

        # Now send the follow-up message
        await interaction.followup.send("followup", ephemeral=True)


class ControlTempChannelsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(name="control", description="Say hello!")
    @discord.app_commands.checks.has_permissions(manage_channels=True)
    async def control(self, interaction: discord.Interaction):
        try:
            # Create an embed with options
            await create_control_menu(self.bot, interaction)
        except Exception as error:
            await handle_command_error(interaction, error)

    @control.error
    async def control_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await handle_user_permission_error("manage_channels", interaction)
        else:
            await handle_command_error(interaction, error)



async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(ControlTempChannelsCog(bot))