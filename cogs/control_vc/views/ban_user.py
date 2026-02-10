import discord


class BanUserView(discord.ui.View):
    def __init__(self, bot, channel):
        super().__init__(timeout=60)
        self.bot = bot
        self.channel = channel
        self.message = None

    @discord.ui.mentionable_select(
        placeholder="Select members or roles to ban",
        min_values=0,
        max_values=25
    )
    async def select_callback(self, select, interaction: discord.Interaction):
        ban_perms = {'connect': False, 'view_channel': False}
        selected_members = select.values
        members = []
        owner_id = self.bot.repos.temp_channels.get_info(self.channel.id).owner_id
        connected_members = self.channel.members

        for member in selected_members:
            if member:
                if member.id != owner_id:
                    members.append(member)
                    await self.channel.set_permissions(
                        member,
                        **ban_perms
                    )
                    if member in connected_members:
                        await member.move_to(None)

        if len(members) > 0:
            embed = discord.Embed(
                title=f"Banned!",
                description=f"Banned {len(members)} member(s)/role(s) from your channel.",
                color=0x00ff00
            )
            embed.set_footer(text="This message will disappear in 10 seconds.")
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)

    async def send_initial_message(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔨 Who would you like to ban from your channel?",
            description=f"They will not be able to see or connect to your channel",
            footer=discord.EmbedFooter("You have 60 seconds to select at least one member."),
            color=0x00ff00
        )
        self.message = await interaction.followup.send(embed=embed, view=self, ephemeral=True, wait=True)  # wait ensures that self.message is set before continuing

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass
