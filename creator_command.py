import discord
from discord.ui import View, Select, Button


class CreateView(View):
    def __init__(self, ctx, bot, timeout):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.message = None

        # Dropdown (own row)
        options = [
            # discord.SelectOption(label="Option 1", value="1"),
            # discord.SelectOption(label="Option 2", value="2"),
            # discord.SelectOption(label="Option 3", value="3"),
        ]
        creator_channel_ids = self.bot.db.get_creator_channel_ids(guild_id=ctx.guild.id)
        for channel_id in creator_channel_ids:
            channel = ctx.guild.get_channel(channel_id)
            if channel:
                options.append(discord.SelectOption(label=f"{channel.name}", value=f"{channel.id}"))

        is_disabled = False
        if len(options) == 0:
            is_disabled = True
            options.append(discord.SelectOption(label="Option 1", value="1"),)

        select = Select(placeholder="Select a creator to edit", options=options, disabled=is_disabled)
        select.callback = self.select_callback
        self.add_item(select)

        # Buttons (same row)
        button1 = Button(label="Create new Creator channel", style=discord.ButtonStyle.success)  # primary, danger
        button1.callback = self.button_callback

        # Add buttons to the view
        self.add_item(button1)

    # Dropdown callback
    async def select_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"You selected", ephemeral=True)

    # Button callback
    async def button_callback(self, interaction: discord.Interaction):
        new_creator_channel = await interaction.guild.create_voice_channel("➕ Create Channel")
        self.bot.db.add_creator_channel(new_creator_channel.guild.id, new_creator_channel.id, "{user}'s channel", 0, 0, 1)

        await interaction.response.send_message(f"Created {new_creator_channel.mention}!", ephemeral=True)
