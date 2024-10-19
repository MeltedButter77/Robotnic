import discord
from discord.ext import commands
import os
import json

# Get the absolute path to the config.json
base_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # One level up
config_path = os.path.join(base_directory, 'config.json')
# Load the configuration from config.json
with open(config_path) as config_file:
    config = json.load(config_file)


class UtilCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="help",
        description="Find out more information about the bot",
    )
    async def help(self, interaction: discord.Interaction):
        """Command to supply the support server link"""
        embed = discord.Embed(
            title="🔧 Help Menu",  # Added emoji to the title
            description="Thanks for using Dr Robotnic! Here is a list of his commands. More are to be added very soon, so keep a look out! 👀",
            color=0x00ff00  # Green color
        )

        embed.set_footer(text="💡 Need more help? Reach out to support below!")

        # Add command fields with emojis
        embed.add_field(
            name="⚙️ /setup_creators",
            value="Allows an admin to setup a channel creator (or channel hub) which dynamically creates voice channels when users join them.",
            inline=False
        )

        # Create a view with a support button
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="🛠️ Support Server",  # Added emoji to the button label
                url=f"{config['support_server']}",
            )
        )
        view.add_item(
            discord.ui.Button(
                label="🌐 Website",  # Added emoji to the button label
                url=f"{config['website']}",
            )
        )

        # Send the embed and view
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(UtilCog(bot))
