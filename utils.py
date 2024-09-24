from discord.ext import commands


class UtilCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def ping(self, ctx: commands.Context):
        """Responds with 'pong' to check bot responsiveness."""
        await ctx.send('pong')


async def setup(bot):
    await bot.add_cog(UtilCommands(bot))
