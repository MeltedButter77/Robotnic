import discord
from discord.ui import View, Select, Button


class CreateEmbed(discord.Embed):
    def __init__(self, guild, bot):
        super().__init__(
            title="title",
            description="description",
            color=discord.Color.blue()
        )

        creator_channel_ids = bot.db.get_creator_channel_ids(guild_id=guild.id)
        for channel_id in creator_channel_ids:
            channel = bot.get_channel(channel_id)
            if channel:
                self.add_field(name=f"{channel.name}", value="Some information", inline=False)


class CreateView(View):
    def __init__(self, ctx, bot, timeout):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.message = None
        self.author = ctx.author

        self.create_items(ctx.guild)

    def create_items(self, guild=None):
        if not guild and self.message:
            guild = self.message.guild

        if guild is None:
            self.bot.logger.error("No guild obj to create items for CreateView")
            return

        # Dropdown (own row)
        options = []
        creator_channel_ids = self.bot.db.get_creator_channel_ids(guild_id=guild.id)
        for channel_id in creator_channel_ids:
            channel = self.bot.get_channel(channel_id)
            if channel:
                options.append(discord.SelectOption(label=f"{channel.name}", value=f"{channel.id}"))

        is_disabled = False
        placeholder = "Select a creator to edit"
        if len(options) == 0:
            is_disabled = True
            options.append(discord.SelectOption(label="Option 1", value="1"),)
            placeholder = "Make a new creator below"

        select = Select(placeholder=placeholder, options=options, disabled=is_disabled)
        select.callback = self.select_callback
        if not is_disabled:  # Removes dropdown entirely instead of disabling
            self.add_item(select)

        # Buttons (same row)
        button1 = Button(label="Create new Creator channel", style=discord.ButtonStyle.success)  # primary, danger
        button1.callback = self.button_callback

        # Add buttons to the view
        self.add_item(button1)

    async def update(self):
        embed = CreateEmbed(self.message.guild, self.bot)
        self.clear_items()
        self.create_items()
        await self.message.edit(view=self, embed=embed)

    # Dropdown callback
    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(f"This is not your menu!", ephemeral=True)

        await interaction.response.send_message(f"You selected", ephemeral=True)

    # Button callback
    async def button_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(f"This is not your menu!", ephemeral=True)

        new_creator_channel = await interaction.guild.create_voice_channel("➕ Create Channel")
        self.bot.db.add_creator_channel(new_creator_channel.guild.id, new_creator_channel.id, "{user}'s channel", 0, 0, 1)

        await interaction.response.send_message(f"Created {new_creator_channel.mention}!", ephemeral=True)
        await self.update()
