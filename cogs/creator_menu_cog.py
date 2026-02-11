import discord
from discord.ext import commands
from cogs.creator_menu.embeds import ListCreatorsEmbed, OptionsEmbed
from cogs.creator_menu.modals import TestModal
from cogs.creator_menu.views import CreateView


class CreatorMenuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(description="Opens a menu to make and edit Creator Channels")
    @discord.default_permissions(administrator=True)
    async def setup(self, ctx):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send_response(f"Sorry {ctx.author.mention}, you require the `administrator` permission to run this command.")

        embeds = [
            OptionsEmbed(),
            ListCreatorsEmbed(guild=ctx.guild, bot=self.bot),
        ]
        view = CreateView(ctx=ctx, bot=self.bot)
        message = await ctx.send_response(f"{ctx.author.mention}", embeds=embeds, view=view)  # , ephemeral=True)
        view.message = message


def setup(bot):
    bot.add_cog(CreatorMenuCog(bot))
