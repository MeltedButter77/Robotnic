from asyncio import wait_for

import discord
from discord.ui import View, Select, Button, Modal, InputText
from discord.ext import commands


class CreatorMenuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(description="Opens a menu to make and edit Creator Channels")
    @discord.default_permissions(administrator=True)
    async def setup_advanced(self, ctx):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send_response(f"Sorry {ctx.author.mention}, you require the `administrator` permission to run this command.")

        embeds = [
            OptionsEmbed(is_advanced=True),
            ListCreatorsEmbed(guild=ctx.guild, bot=self.bot, is_advanced=True),
        ]
        view = CreateView(ctx=ctx, bot=self.bot, is_advanced=True)
        message = await ctx.send_response(f"{ctx.author.mention}", embeds=embeds, view=view)  # , ephemeral=True)
        view.message = message

    @discord.slash_command(description="Opens a menu to make and edit Creator Channels")
    @discord.default_permissions(administrator=True)
    async def setup(self, ctx):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send_response(f"Sorry {ctx.author.mention}, you require the `administrator` permission to run this command.")

        embeds = [
            OptionsEmbed(),
            ListCreatorsEmbed(guild=ctx.guild, bot=self.bot),
        ]
        view = CreateView(ctx=ctx, bot=self.bot)
        message = await ctx.send_response(f"{ctx.author.mention}", embeds=embeds, view=view)  # , ephemeral=True)
        view.message = message


def setup(bot):
    bot.add_cog(CreatorMenuCog(bot))


class EditModal(Modal):
    def __init__(self, view, creator_id, is_advanced: bool = False):
        super().__init__(title="Example Modal")
        self.view = view
        self.creator_id = creator_id

        # Add input fields
        self.add_item(InputText(label="Name of Temporary Channel Created", placeholder="Can include variables {user}, {activity} or {count}", required=False))
        if is_advanced:
            self.add_item(InputText(label="User Limit", placeholder="Enter integer 0-99 (0 = Unlimited)", required=False))
            self.add_item(InputText(label="Temp Channel Category ID", placeholder="Enter 0 (for same as creator) or category ID", required=False))
            self.add_item(InputText(label="Temp Channel Permissions", placeholder="Enter integer 0-2 (differences explained in /creator menu)", required=False))

    async def callback(self, interaction: discord.Interaction):
        errors = []

        db_creator_channel_info = self.view.bot.db.get_creator_channel_info(self.creator_id)

        # Validate Child name length
        child_name = self.children[0].value.strip() or db_creator_channel_info.child_name
        if len(child_name) > 100:
            errors.append("Child name must be under 100 characters.")

        # Validate user limit
        user_limit_raw = self.children[1].value.strip()
        if user_limit_raw == "":
            user_limit = db_creator_channel_info.user_limit
        else:
            try:
                user_limit = int(user_limit_raw)
                if not (0 <= user_limit <= 99):
                    errors.append("User limit must be an integer between `0` and `99` inclusive.")
            except ValueError:
                errors.append("User limit must be an integer.")

        # Validate Child Category ID
        category_raw = self.children[2].value.strip()
        if category_raw == "":
            child_category_id = db_creator_channel_info.child_category_id
        else:
            try:
                child_category_id = int(category_raw)
                category = self.view.bot.get_channel(child_category_id)
                if child_category_id < 0 or category is None:
                    errors.append("Category ID must be `0` or a valid category ID (positive integer).")
            except ValueError:
                errors.append("Category ID must be an integer.")

        # Validate Child Overwrite optiuons
        overwrites_raw = self.children[3].value.strip()
        if overwrites_raw == "":
            child_overwrites = db_creator_channel_info.child_overwrites
        else:
            try:
                child_overwrites = int(overwrites_raw)
                if child_overwrites not in (0, 1, 2):
                    errors.append("Permissions must be `0` (None), `1` (From Creator), or `2` (From Category).")
            except ValueError:
                errors.append("Permissions must be an integer `0` (None), `1` (From Creator), or `2` (From Category).")

        # --- Handle Errors ---
        if errors:
            await interaction.response.send_message(
                f"Invalid input:\n" + "\n".join(f"- {error}" for error in errors),
                ephemeral=True
            )
            await self.view.update()
            return

        self.view.bot.db.edit_creator_channel(
            channel_id=self.creator_id,
            child_name=child_name,
            user_limit=user_limit,
            child_category_id=child_category_id,
            child_overwrites=child_overwrites
        )

        await interaction.response.send_message(
            f"Creator channel updated!",
            ephemeral=True
        )
        await self.view.update()


class OptionsEmbed(discord.Embed):
    def __init__(self, is_advanced: bool = False):
        super().__init__(
            title="Creator Channels' Options",
            color=discord.Color.blue()
        )

        self.add_field(name="1. Child Name", value="This is the pattern the created channel's names will follow\n> Available Variables: `{user}`, `{count}` & `{activity}`\n> (Default: `{user}'s Room`)", inline=False)
        if is_advanced:
            self.add_field(name="2. User Limit", value="The user limit set on created channels\n> `0` = Unlimited\n> Accepts any integer `0`-`99` inclusive (Default: `0`)", inline=False)
            self.add_field(name="3. Category", value="Which category created channels are placed in\n> `0` = Same as creator\n> Accepts category ID as input (Default: `0`)", inline=False)
            self.add_field(name="4. Permissions", value="Whether the created channels should have the same permissions as the creator, category or none at all\n> `0` = No Permissions\n> `1` = Creator Channel\n> `2` = Relevant Category\n> Accepts integers `0`-`2` inclusive (Default: `1`)", inline=False)
        else:
            self.add_field(name="For more Options, use `/setup_advanced` instead", value="", inline=False)


class ListCreatorsEmbed(discord.Embed):
    def __init__(self, guild, bot, is_advanced: bool = False):
        super().__init__(
            title="Selected Options for each Creator Channel",
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

                if is_advanced:
                    desc = f"Names of Created Channels:\n> `{child_name}`\nUser Limit:\n> `{user_limit}`\nCategory:\n> `{category}`\nPermission Inheritance:\n> `{overwrites}`"
                else:
                    desc = f"Name Scheme:\n> `{child_name}`"
                self.add_field(name=f"#{i+1}. {channel.mention}", value=desc, inline=True)

        if not is_advanced:
            self.add_field(name="For more Options, use `/setup_advanced` instead", value="", inline=False)

        # Handle case of no fields. Also prevents error of no embed content
        if len(self.fields) < 1:
            self.title = "No Creators to list. Make a new one below."


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
        await self.message.edit(view=None, embeds=[], content="> Message timed out. Please run the command again.")
