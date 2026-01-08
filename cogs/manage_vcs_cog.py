import discord
from discord.ext import commands
from cogs.manage_vcs.events import handle_voice_state_update, handle_presence_update


class ManageVcsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        await handle_voice_state_update(self.bot, member, before, after)

    # If user's activity changes while in a temp vc, update its name
    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        await handle_presence_update(self.bot, before, after)


def setup(bot):
    bot.add_cog(ManageVcsCog(bot))
