import discord
from discord.ext import commands


class GeneralCCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(description="Responds with bot latency.")
    @discord.default_permissions(administrator=True)
    async def ping(self, ctx):
        await ctx.respond(f"Pong! Latency is {self.bot.latency}")


def setup(bot):
    bot.add_cog(GeneralCCog(bot))
