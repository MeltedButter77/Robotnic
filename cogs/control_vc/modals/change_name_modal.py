import datetime
import discord
import requests
from cogs.control_vc.embed_updates import update_info_embed
from cogs.manage_vcs.update_name import update_channel_name_and_control_msg


async def check_profanity(logger, session, text: str) -> dict | None:
    try:
        response = session.post(
            "https://vector.profanity.dev",
            json={"message": text},
            timeout=3,
        )
        return response.json()
    except Exception as e:
        logger.warning(f"Profanity API failed, skipping check. {e}")
        return None


class ChangeNameModal(discord.ui.Modal):
    def __init__(self, bot, channel):
        super().__init__(title="Edit Your Channel")
        self.bot = bot
        self.channel = channel

        # Define the text inputs
        self.channel_name = discord.ui.InputText(
            label="Channel Name (Blank = Default)",
            placeholder=f"{channel.name}",
            required=False,
            max_length=25
        )

        self.add_item(self.channel_name)

    async def callback(self, interaction: discord.Interaction):
        # Update the channel
        channel_name = str(self.channel_name.value or self.channel.name)
        if len(channel_name) > 100:
            channel_name = channel_name[:97] + "..."

        profanity_check_setting = self.bot.repos.guild_settings.get_profanity_filter(interaction.guild.id)["profanity_filter"]
        if profanity_check_setting is not None:
            profanity_check = await check_profanity(self.bot.logger, requests, channel_name)

            if profanity_check["isProfanity"]:
                embed = discord.Embed(
                    title="TempChannel Blocked Rename",
                    description="",
                    color=discord.Color.red()
                )
                embed.add_field(name="Channel",
                                value=f"`{self.channel.name}` (`{self.channel.id})`",
                                inline=False)
                embed.add_field(name="User",
                                value=f"`{interaction.user.display_name}` (`{interaction.user.display_name}`, `{interaction.user.id}`)",
                                inline=False)
                embed.add_field(name="New Name (Blocked)",
                                value=f"`{channel_name}`",
                                inline=False)
                embed.add_field(name="Flagged for",
                                value=f"`{profanity_check["flaggedFor"]}`",
                                inline=False)
                embed.timestamp = datetime.datetime.now()
                embed.set_footer(text="Toggle with /settings")
                await self.bot.GuildLogService.send(event="profanity_block", guild=interaction.guild, message=f"", embed=embed)

                if profanity_check_setting == "alert & block":
                    return await interaction.response.send_message("Sorry, that input was flagged for profanity.", ephemeral=True, delete_after=90)

        # If inputted name, schedule update channel and update db
        if self.channel_name.value:
            await self.bot.TempChannelRenamer.schedule(self.channel, channel_name)
            await update_info_embed(self.bot, self.channel, title=channel_name)
            self.bot.repos.temp_channels.set_is_renamed(self.channel.id, True)
        else:
            # If left blank the channel rename override is reset
            self.bot.repos.temp_channels.set_is_renamed(self.channel.id, False)
            await update_channel_name_and_control_msg(self.bot, [self.channel.id])

        embed = discord.Embed(
            title="Changes Saved",
            description="Your channel will update as soon as possible. Sometimes Discord will limit updates if they are too frequent, please be patient.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="This message will disappear in 30 seconds.")
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=30)

        # Sends messages in the guild log channel - uses get_guild_logs_channel_id instead of get_guild_settings for read efficiency
        embed = discord.Embed(
            title="TempChannel Rename",
            description="",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Old Channel",
                        value=f"`{self.channel.name}` (`{self.channel.id}`)",
                        inline=False)
        embed.add_field(name="User",
                        value=f"`{interaction.user.display_name}` (`{interaction.user.display_name}`, `{interaction.user.id}`)",
                        inline=False)
        embed.add_field(name="New Name",
                        value=f"`{channel_name}`",
                        inline=False)
        embed.timestamp = datetime.datetime.now()
        await self.bot.GuildLogService.send(event="channel_rename", guild=interaction.guild, message=f"", embed=embed)
