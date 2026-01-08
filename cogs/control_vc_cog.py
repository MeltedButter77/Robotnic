from discord.ext import commands


class Control_Vc_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(Control_Vc_cog(bot))
