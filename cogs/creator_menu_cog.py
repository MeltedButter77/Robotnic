import discord
from discord.ext import commands
from cogs.creator_menu.embeds import ListCreatorsEmbed
from cogs.creator_menu.views import CreateView


class CreatorMenuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(description="Opens a menu to make and edit Creator Channels")
    @discord.default_permissions(administrator=True)
    async def setup(self, ctx):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send_response(f"Sorry {ctx.author.mention}, you require the `administrator` permission to run this command.")

        creator_channel_ids = self.bot.repos.creator_channels.get_ids(ctx.guild.id)
        for channel_id in creator_channel_ids:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                self.bot.logger.debug(f"Removing unfound/deleted creator channel from database")
                self.bot.repos.creator_channels.remove(channel_id)

        embeds = [ListCreatorsEmbed(guild=ctx.guild, bot=self.bot)]
        view = CreateView(ctx=ctx, bot=self.bot)
        message = await ctx.send_response(f"{ctx.author.mention}", embeds=embeds, view=view)  # , ephemeral=True)
        view.message = message


def setup(bot):
    bot.add_cog(CreatorMenuCog(bot))
