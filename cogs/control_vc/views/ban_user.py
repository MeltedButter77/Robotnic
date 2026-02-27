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
    async def ban_select_callback(self, select, interaction: discord.Interaction):
        ban_perms = {
            "connect": False,
            "view_channel": False
        }

        owner_id = self.bot.repos.temp_channels.get_info(self.channel.id).owner_id
        connected_members = self.channel.members
        affected = []

        for target in select.values:
            if not target:
                continue

            if isinstance(target, discord.Member) and target.id == owner_id:
                continue

            await self.channel.set_permissions(target, **ban_perms)
            affected.append(target)

            if isinstance(target, discord.Member) and target in connected_members:
                await target.move_to(None)

        if affected:
            embed = discord.Embed(
                title="Banned!",
                description=f"Banned {len(affected)} member(s)/role(s) from your channel.",
                color=0x00FF00
            )
            embed.set_footer(text="This message will disappear in 10 seconds.")
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
                delete_after=10
            )

    # ---- ALLOW SELECT ----
    @discord.ui.mentionable_select(
        placeholder="Select members or roles to allow",
        min_values=0,
        max_values=25
    )
    async def allow_select_callback(self, select, interaction: discord.Interaction):
        allow_perms = {
            "connect": True,
            "view_channel": True
        }

        affected = []

        for target in select.values:
            if not target:
                continue

            await self.channel.set_permissions(target, **allow_perms)
            affected.append(target)

        if affected:
            embed = discord.Embed(
                title="Allowed!",
                description=f"Allowed {len(affected)} member(s)/role(s) in your channel.",
                color=0x00FF00
            )
            embed.set_footer(text="This message will disappear in 10 seconds.")
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
                delete_after=10
            )

    async def send_initial_message(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔨 Manage access to your channel",
            description=(
                "Use the menus below to ban or allow members/roles.\n"
                "Banned users cannot view or connect to the channel."
            ),
            color=0x00FF00
        )
        embed.set_footer(text="You have 60 seconds to make selections.")

        self.message = await interaction.followup.send(
            embed=embed,
            view=self,
            ephemeral=True,
            wait=True
        )

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass