import discord
from discord.ui import View, Select, Button, Modal, InputText
from cogs.creator_menu.embeds import ListCreatorsEmbed
from cogs.creator_menu.modals import EditModal


class CreateView(View):
    def __init__(self, ctx, bot, is_advanced: bool = False):
        super().__init__()
        self.bot = bot
        self.message = None
        self.author = ctx.author
        self.is_advanced = is_advanced

        self.create_items(ctx.guild)

    def create_items(self, guild=None):
        # We require the guild id to get all creator channels for the guild
        # Either it's passed in or in self.update which has no inputs, we use the guild of the stored message
        # This doesn't work on first create as the view is made before the message attribute is updated after
        if not guild and self.message:
            guild = self.message.guild

        if guild is None:
            self.bot.logger.error("No guild obj to create items for CreateView")
            return

        # Dropdown (own row)
        options = []
        creator_channel_ids = self.bot.db.get_creator_channel_ids(guild_id=guild.id)
        for i, channel_id in enumerate(creator_channel_ids):
            channel = self.bot.get_channel(channel_id)
            if channel:
                options.append(discord.SelectOption(label=f"Edit #{i+1}. {channel.name}", value=f"{channel.id}"))

        # If the dropdown has no options, add a placeholder one and disable it showing only the placeholder text
        is_disabled = False
        placeholder = "Select a Creator to edit"
        if len(options) == 0:
            is_disabled = True
            options.append(discord.SelectOption(label="Option 1", value="1"),)
            placeholder = "Make a new creator below"

        select = Select(placeholder=placeholder, options=options, disabled=is_disabled)
        select.callback = self.select_callback
        if not is_disabled:  # Removes dropdown entirely instead of disabling
            self.add_item(select)

        # Buttons (same row)
        button1 = Button(label=f"Make new Creator", style=discord.ButtonStyle.success)  # primary, danger
        button1.callback = self.button_callback

        # Add buttons to the view
        self.add_item(button1)

    async def update(self):
        embeds = [
            self.message.embeds[0],
            ListCreatorsEmbed(self.message.guild, self.bot, is_advanced=self.is_advanced)
        ]
        self.clear_items()
        self.create_items()
        await self.message.edit(view=self, embeds=embeds)

    # Dropdown callback
    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(f"This is not your menu!", ephemeral=True)

        modal = EditModal(self, creator_id=interaction.data["values"][0], is_advanced=self.is_advanced)
        await interaction.response.send_modal(modal)
        await self.update()  # If modal isnt submitted the dropdown wont be already used/selected

    # Button callback
    async def button_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(f"This is not your menu!", ephemeral=True)

        new_creator_channel = await interaction.guild.create_voice_channel("➕ Create Channel")
        self.bot.db.add_creator_channel(new_creator_channel.guild.id, new_creator_channel.id, "{user}'s Room", 0, 0, 1)

        embeds = [discord.Embed(), discord.Embed()]
        embeds[0].title = f"Created {new_creator_channel.mention}! Join to see how it works."
        embeds[1].color = discord.Color.green()
        embeds[1].title = "For Best Results:"
        embeds[1].add_field(name="", value="**Move the channel** to your desired location and **change its name** if you wish to distinguish it from other Creator Channels.", inline=True)
        embeds[1].add_field(name="", value="If you wish to edit the **name scheme** of temp channels, please **select a Creator Channel to edit above**", inline=True)
        embeds[1].add_field(name="", value="Any temp channels it creates, by default, will **inherit the same permissions as the creator**.", inline=True)
        embeds[1].footer = discord.EmbedFooter("This message will disappear in 60 seconds")
        await interaction.response.send_message(f"", embeds=embeds, ephemeral=True, delete_after=60)
        await self.update()

        if self.bot.notification_channel:
            await self.bot.notification_channel.send(f"Creator Channel was made in `{interaction.guild.name}` by `{interaction.user}`")

    async def on_timeout(self):
        try:
            await self.message.edit(view=None, embeds=[], content="> Message timed out. Please run the command again.")
        except Exception as e:
            self.bot.logger.error(f"Unable to update CreateView message after timeout, message likely deleted before timeout.")
