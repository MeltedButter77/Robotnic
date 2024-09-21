from discord.ext import commands


class UtilCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def sync(self, ctx):
        """Synchronize the command tree."""
        if ctx.author.id != 344531337174319106:
            return await ctx.send('You cannot use this command')
        await ctx.send('Syncing...')
        synced_commands = await self.bot.tree.sync()
        await ctx.send(f'Synced {len(synced_commands)} commands!')

    @commands.hybrid_command()
    async def ping(self, ctx: commands.Context):
        """Responds with 'pong' to check bot responsiveness."""
        await ctx.send('pong')


async def setup(bot):
    await bot.add_cog(UtilCommands(bot))
