import discord
from discord.ext import commands
from cogs.settings.embeds import ChannelControlsEmbed
from cogs.settings.views import ChannelControlsView, LogEventsView


class SettingsMenuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    settings = discord.SlashCommandGroup(
        "settings",
        "Change Guild Settings",
        default_member_permissions=discord.Permissions(administrator=True),
    )

    @settings.command(description="Set the log channel")
    async def log_channel(
        self,
        ctx: discord.ApplicationContext,
        log_channel: discord.Option(
            discord.TextChannel,
            "Required text channel",
            required=True
        ),
    ):
        self.bot.repos.guild_settings.edit(ctx.guild_id, logs_channel_id=log_channel.id)

        await ctx.respond(
            f"Set Log Channel as {log_channel.mention}"
        )

    @settings.command(description="Disable the log channel")
    async def log_channel_disable(
        self,
        ctx: discord.ApplicationContext,
    ):
        self.bot.repos.guild_settings.edit(ctx.guild_id, logs_channel_id=0)
        await ctx.respond(
            f"Cleared Log Channel. Logging is now disabled."
        )

    @settings.command(description="Select which controls users should have access to by default")
    async def enabled_controls(
        self,
        ctx: discord.ApplicationContext,
):
        view = ChannelControlsView(ctx=ctx, bot=self.bot)
        message = await ctx.send_response(f"{ctx.author.mention}", embed=ChannelControlsEmbed(), view=view)
        view.message = message

    @settings.command(description="Whether the bot should ping the owner of the temp channel when the controls are sent")
    async def mention_owner(
        self,
        ctx: discord.ApplicationContext,
        should_mention: discord.Option(
            bool,
            "Enable or disable pinging the owner to alert them of the controls they have access to.",
            required=True
        )
    ):
        text = "Enabled"
        if not should_mention:
            text = "Disabled"

        self.bot.repos.guild_settings.edit(ctx.guild_id, mention_owner=should_mention)
        await ctx.respond(
            f"Mention Owner `{text}`"
        )

    @settings.command(description="Select which events will be logged")
    async def enabled_log_events(
        self,
        ctx: discord.ApplicationContext,
    ):
        view = LogEventsView(ctx=ctx, bot=self.bot)
        message = await ctx.send_response(f"{ctx.author.mention}", embed=ChannelControlsEmbed(), view=view)
        view.message = message

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
