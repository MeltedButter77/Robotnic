import datetime
import discord
import requests
from cogs.control_vc.embed_updates import update_info_embed
from cogs.manage_vcs.update_name import update_channel_name_and_control_msg


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

        log_channel = self.bot.get_channel(self.bot.db.get_guild_logs_channel_id(interaction.guild.id)["logs_channel_id"])
        profanity_check_setting = self.bot.db.get_guild_profanity_filter(interaction.guild.id)["profanity_filter"]
        if profanity_check_setting:
            profanity_check_response = requests.post(
                "https://vector.profanity.dev",
                headers={"Content-Type": "application/json"},
                json={"message": channel_name},
            )
            profanity_check = profanity_check_response.json()

            if profanity_check["isProfanity"]:
                if log_channel:
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
                    await log_channel.send(f"", embed=embed)

                return await interaction.response.send_message("Sorry, that input was flagged for profanity.", ephemeral=True, delete_after=90)

        # If inputted name, schedule update channel and update db
        if self.channel_name.value:
            await self.bot.renamer.schedule(self.channel, channel_name)
            await update_info_embed(self.bot, self.channel, title=channel_name)
            self.bot.db.set_temp_channel_is_renamed(self.channel.id, True)
        else:
            # If left blank the channel rename override is reset
            self.bot.db.set_temp_channel_is_renamed(self.channel.id, False)
            await update_channel_name_and_control_msg(self.bot, [self.channel.id])

        embed = discord.Embed(
            title="Changes Saved",
            description="Your channel will update as soon as possible. Sometimes Discord will limit updates if they are too frequent, please be patient.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="This message will disappear in 30 seconds.")
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=30)

        # Sends messages in the guild log channel - uses get_guild_logs_channel_id instead of get_guild_settings for read efficiency
        if log_channel:
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
            await log_channel.send(f"", embed=embed)


class UserLimitModal(discord.ui.Modal):
    def __init__(self, bot, channel):
        super().__init__(title="Edit Your Channel")
        self.bot = bot
        self.channel = channel

        # Define the text inputs
        self.user_limit = discord.ui.InputText(
            label="User Limit (Unlimited = 0)",
            placeholder=f"{channel.user_limit}",
            required=False,
            max_length=2
        )

        self.add_item(self.user_limit)

    async def callback(self, interaction: discord.Interaction):
        user_limit = self.user_limit.value or str(self.channel.user_limit)

        if not user_limit.isnumeric():
            embed = discord.Embed(
                title="Invalid Input",
                description="User limit must be a number.",
                color=discord.Color.red()
            )
            embed.set_footer(text="This message will disappear in 15 seconds.")
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=15)
            return

        # Update the channel user limit
        if user_limit != self.channel.user_limit:
            await self.channel.edit(user_limit=int(user_limit))
        await update_info_embed(self.bot, self.channel, user_limit=user_limit)  # Only required if limit is displayed in info embed. hardcoded on/off atm

        embed = discord.Embed(
            title="Changes Saved",
            description=f"Channel limit changed to {user_limit}",
            color=discord.Color.blue()
        )
        embed.set_footer(text="This message will disappear in 15 seconds.")
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=15)
