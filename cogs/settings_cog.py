import discord
from discord.ext import commands
from cogs.settings.modals import SettingsModal, LogsModal


class SettingsMenuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    settings = discord.SlashCommandGroup(
        "settings",
        "Change Guild Settings",
        default_member_permissions=discord.Permissions(administrator=True),
    )

    @settings.command(description="Select which controls users should have access to by default")
    async def logging(
            self,
            ctx: discord.ApplicationContext,
    ):
        await ctx.send_modal(LogsModal(self.bot, ctx))

        embed = discord.Embed(
            title="",
            description=f"Make sure to click \"SUBMIT\" after editing the pop-up menu.",
            color=discord.Color.yellow()
        )
        embed.set_footer(text="This message will disappear in 30 seconds.")
        await ctx.send_followup(embed=embed, ephemeral=True, delete_after=30)

    @settings.command(description="Select which controls users should have access to by default")
    async def controls(
        self,
        ctx: discord.ApplicationContext,
    ):
        await ctx.send_modal(SettingsModal(self.bot, ctx))

        embed = discord.Embed(
            title="",
            description=f"Make sure to click \"SUBMIT\" after editing the pop-up menu.",
            color=discord.Color.yellow()
        )
        embed.set_footer(text="This message will disappear in 30 seconds.")
        await ctx.send_followup(embed=embed, ephemeral=True, delete_after=30)

    @settings.command(description="Set the profanity check in channel names")
    async def profanity_filter(
        self,
        ctx: discord.ApplicationContext,
        mode: discord.Option(
            str,
            choices=["off", "alert", "alert & block"],
            description="Filter mode, alert will send a profanity alert in the logs channel."
        )
    ):
        self.bot.repos.guild_settings.edit(ctx.guild_id, profanity_filter=mode)
        await ctx.respond(
            f"profanity filter set to `{mode}`"
        )


def setup(bot):
    bot.add_cog(SettingsMenuCog(bot))
