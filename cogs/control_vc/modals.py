import discord
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
        log_channel = self.bot.get_channel(self.bot.db.get_guild_logs_channel_id(interaction.guild.id)["logs_channel_id"])
        if log_channel:
            await log_channel.send(f"User user `{interaction.user} ({interaction.user.id}`) renamed Temp Channel `{self.channel.name} ({self.channel.id}`) to `{channel_name}`")


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
