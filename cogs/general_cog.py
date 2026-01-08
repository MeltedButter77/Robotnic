import discord
from discord.ext import commands
from cogs.general.embeds import DonateEmbed
from cogs.general.views import ButtonsView


class GeneralCCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(description="Responds with bot latency.")
    @discord.default_permissions(administrator=True)
    async def ping(self, ctx):
        await ctx.respond(f"Pong! Latency is {self.bot.latency}")

    @discord.slash_command(description="Get support using Robotnic or support the creator.")
    async def support(self, ctx):
        embeds = [
            DonateEmbed()
        ]
        await ctx.respond(f"{ctx.user.mention}", embeds=embeds, view=ButtonsView())

    # Aliases to /support
    @discord.slash_command(description="Get help using Robotnic or support the creator.")
    async def help(self, ctx):
        await self.support.callback(self, ctx)

    @discord.slash_command(description="Support the creator of Robotnic.")
    async def donate(self, ctx):
        await self.support.callback(self, ctx)


def setup(bot):
    bot.add_cog(GeneralCCog(bot))
