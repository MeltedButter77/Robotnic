import discord


class ControlVcContextMenus:
    def __init__(self, bot):
        self.bot = bot

    # RIGHT CLICK USER -> APPS -> BAN USER
    @discord.user_command(name="Ban User")
    async def ban_user(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Member
    ):
        if not isinstance(ctx.author, discord.Member):
            return

        voice_channel = (
            ctx.author.voice.channel
            if ctx.author.voice
            else None
        )

        if voice_channel is None:
            await ctx.respond(
                "You must be in your controlled voice channel to use this.",
                ephemeral=True
            )
            return

        channel_info = self.bot.repos.temp_channels.get_info(
            voice_channel.id
        )

        if channel_info is None:
            await ctx.respond(
                "This is not a controlled voice channel.",
                ephemeral=True
            )
            return

        if channel_info.owner_id != ctx.author.id:
            await ctx.respond(
                "Only the owner of this voice channel can ban users.",
                ephemeral=True
            )
            return

        if user.id == ctx.author.id:
            await ctx.respond(
                "You cannot ban yourself from your own channel.",
                ephemeral=True
            )
            return

        if user.id == self.bot.user.id:
            await ctx.respond(
                "You cannot ban the bot.",
                ephemeral=True
            )
            return

        await voice_channel.set_permissions(
            user,
            connect=False,
            view_channel=False
        )

        if user in voice_channel.members:
            try:
                await user.move_to(None)
            except discord.Forbidden:
                pass

        embed = discord.Embed(
            title="🔨 User Banned",
            description=(
                f"{user.mention} has been banned from "
                f"{voice_channel.mention}."
            ),
            color=0xFF0000
        )
        embed.footer = f"This message will be deleted in 30 seconds."

        await ctx.respond(
            embed=embed,
            ephemeral=True,
            delete_after=30
        )

    # RIGHT CLICK USER -> APPS -> ALLOW USER
    @discord.user_command(name="Allow User")
    async def allow_user(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Member
    ):
        if not isinstance(ctx.author, discord.Member):
            return

        voice_channel = (
            ctx.author.voice.channel
            if ctx.author.voice
            else None
        )

        if voice_channel is None:
            await ctx.respond(
                "You must be in your controlled voice channel to use this.",
                ephemeral=True
            )
            return

        channel_info = self.bot.repos.temp_channels.get_info(
            voice_channel.id
        )

        if channel_info is None:
            await ctx.respond(
                "This is not a controlled voice channel.",
                ephemeral=True
            )
            return

        if channel_info.owner_id != ctx.author.id:
            await ctx.respond(
                "Only the owner of this voice channel can allow users.",
                ephemeral=True
            )
            return

        await voice_channel.set_permissions(
            user,
            connect=True,
            view_channel=True
        )

        embed = discord.Embed(
            title="✅ User Allowed",
            description=(
                f"{user.mention} has been allowed to access "
                f"{voice_channel.mention}."
            ),
            color=0x00FF00
        )
        embed.footer = f"This message will be deleted in 30 seconds."

        await ctx.respond(
            embed=embed,
            ephemeral=True,
            delete_after=30
        )