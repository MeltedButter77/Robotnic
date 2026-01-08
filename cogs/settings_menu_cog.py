import discord
from discord.ext import commands
from cogs.settings_menu.embeds import MessageEmbed
from cogs.settings_menu.views import SettingsView


class SettingsMenuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(description="Change Guild Settings")
    @discord.default_permissions(administrator=True)
    async def settings(self, ctx):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send_response(f"Sorry {ctx.author.mention}, you require the `administrator` permission to run this command.")

        view = SettingsView(ctx=ctx, bot=self.bot)
        message = await ctx.send_response(f"{ctx.author.mention}", embed=MessageEmbed(), view=view)  # , ephemeral=True)
        view.message = message


def setup(bot):
    bot.add_cog(SettingsMenuCog(bot))
