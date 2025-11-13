import discord
from discord.ui import View, Select, Button, Modal, InputText


class EditModal(Modal):
    def __init__(self, view):
        super().__init__(title="Example Modal")
        self.view = view

        # Add input fields
        self.add_item(InputText(label="Child Name", placeholder="Enter your name", required=False))
        self.add_item(InputText(label="User Limit", placeholder="Enter integer 0-99 (0 = Unlimited)", required=False))
        self.add_item(InputText(label="Child Category ID", placeholder="Enter 0 or category ID", required=False))
        self.add_item(InputText(label="Child Permissions", placeholder="Enter integer 0-2 (1 recommended)", required=False))

    async def callback(self, interaction: discord.Interaction):
        child_name = self.children[0].value
        user_limit = self.children[1].value
        child_category_id = self.children[2].value
        child_overwrites = self.children[3].value

        await interaction.response.send_message(
            f"Creator channel updated!",
            ephemeral=True
        )
        await self.view.update()


class OptionsEmbed(discord.Embed):
    def __init__(self, guild, bot):
        super().__init__(
            title="Creator Channels' Options",
            color=discord.Color.blue()
        )

        self.add_field(name="1. Child Name", value="This is the pattern the created channel's names will follow\n> Available Variables: `{user}`, `{count}` & `{activity}`\n> (Default: `{user}'s channel`)", inline=False)
        self.add_field(name="2. User Limit", value="The user limit set on created channels\n> `0` = Unlimited\n> Accepts any integer `0`-`99` inclusive (Default: `0`)", inline=False)
        self.add_field(name="3. Category", value="Which category created channels are placed in\n> `0` = Same as creator\n> Accepts category ID as input (Default: `0`)", inline=False)
        self.add_field(name="4. Permissions", value="Whether the created channels should have the same permissions as the creator, category or none at all\n> `0` = No Permissions\n> `1` = Creator Channel\n> `2` = Relevant Category\n> Accepts integers `0`-`2` inclusive (Default: `1`)", inline=False)


class ListCreatorsEmbed(discord.Embed):
    def __init__(self, guild, bot):
        super().__init__(
            color=discord.Color.green()
        )

        # Creates a field for each creator channel
        creator_channel_ids = bot.db.get_creator_channel_ids(guild_id=guild.id)
        for i, channel_id in enumerate(creator_channel_ids):
            channel = bot.get_channel(channel_id)
            creator_info = bot.db.get_creator_channel_info(channel_id)

            if channel:
                child_name = creator_info.child_name
                user_limit = "0 = Unlimited" if creator_info.user_limit == 0 else creator_info.user_limit

                category = "0 = Same as Creator" if creator_info.child_category_id == 0 else creator_info.child_category_id

                if creator_info.child_overwrites == 1:
                    overwrites = "1 = From Creator channel"
                elif creator_info.child_overwrites == 2:
                    overwrites = "2 = From category"
                else:  # should be for case 0
                    overwrites = "0 = None. Permissions are cleared"

                desc = f"Created Names:\n> `{child_name}`\nUser Limit:\n> `{user_limit}`\nCategory:\n> `{category}`\nPermission Inheritance:\n> `{overwrites}`"
                self.add_field(name=f"#{i+1}. {channel.mention}", value=desc, inline=True)

        # Handle case of no fields. Also prevents error of no embed content
        if len(self.fields) < 1:
            self.title = "No Creators to list. Make a new one below."


class CreateView(View):
    def __init__(self, ctx, bot, timeout):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.message = None
        self.author = ctx.author

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
        button1 = Button(label="Create new Creator channel", style=discord.ButtonStyle.success)  # primary, danger
        button1.callback = self.button_callback

        # Add buttons to the view
        self.add_item(button1)

    async def update(self):
        embeds = [
            self.message.embeds[0],
            ListCreatorsEmbed(self.message.guild, self.bot)
        ]
        self.clear_items()
        self.create_items()
        await self.message.edit(view=self, embeds=embeds)

    # Dropdown callback
    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(f"This is not your menu!", ephemeral=True)

        modal = EditModal(self)
        await interaction.response.send_modal(modal)

    # Button callback
    async def button_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(f"This is not your menu!", ephemeral=True)

        new_creator_channel = await interaction.guild.create_voice_channel("➕ Create Channel")
        self.bot.db.add_creator_channel(new_creator_channel.guild.id, new_creator_channel.id, "{user}'s channel", 0, 0, 1)

        await interaction.response.send_message(f"Created {new_creator_channel.mention}!", ephemeral=True)
        await self.update()
