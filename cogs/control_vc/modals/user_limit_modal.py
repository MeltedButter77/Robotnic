import discord
from cogs.control_vc.embed_updates import update_info_embed


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
