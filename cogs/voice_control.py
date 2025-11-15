from discord.ui import View, Select, Button, Modal, InputText
from enum import Enum
import discord
from discord.ext import commands


class VoiceControlCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(VoiceControlCog(bot))


class ChannelState(Enum):
    PUBLIC = 0
    LOCKED = 1
    HIDDEN = 2


async def update_info_embed(bot, channel):
    control_message = None
    async for message in channel.history(limit=1, oldest_first=True):
        control_message = message
    if control_message is None:
        print("Failed to find control message")
        return
    embeds = control_message.embeds
    embeds[0] = ChannelInfoEmbed(bot, channel)
    await control_message.edit(embeds=embeds)


class ControlIconsEmbed(discord.Embed):
    def __init__(self):
        super().__init__(
            title="",
            description="",
            color=0x00ff00
        )

        self.add_field(name="🔧 Modify", value="", inline=True)
        self.add_field(name="👢 Kick", value="", inline=True)
        self.add_field(name="🎁 Give/Claim", value="", inline=True)
        self.add_field(name="🧽 Clear", value="", inline=True)
        self.add_field(name="🔨 Ban", value="", inline=True)
        self.add_field(name="🗑️ Delete", value="", inline=True)
        self.add_field(name="🌐 Public", value="", inline=True)
        self.add_field(name="🙈 Hide", value="", inline=True)
        self.add_field(name="🔒 Lock", value="", inline=True)


class ChannelInfoEmbed(discord.Embed):
    def __init__(self, bot, temp_channel):
        super().__init__(
            color=discord.Color.blue()
        )

        self.title = f"{temp_channel.name}"

        temp_channel_info = bot.db.get_temp_channel_info(temp_channel.id)

        owner_id = temp_channel_info.owner_id
        if owner_id:
            if owner_id is not None:
                owner = f"<@{owner_id}>"
            else:
                owner = "None, available to claim"
        else:
            owner = "None, available to claim"
        self.add_field(name="Owner", value=f"{owner}", inline=True)

        limit = temp_channel.user_limit
        if limit == 0:
            limit = "♾️ Unlimited"

        region = temp_channel.rtc_region
        if region is None:
            region = "🌍 Auto"

        channel_state_id = temp_channel_info.channel_state
        if channel_state_id == ChannelState.PUBLIC.value:
            channel_state = "🌐 Public"
        elif channel_state_id == ChannelState.LOCKED.value:
            channel_state = "🔒 Locked"
        elif channel_state_id == ChannelState.HIDDEN.value:
            channel_state = "🙈 Hidden"
        else:
            channel_state = "None"

        self.add_field(name="Limit", value=f"{limit}", inline=True)
        self.add_field(name="Region", value=f"{region}", inline=True)
        self.add_field(name="Access", value=f"{channel_state}", inline=True)


class ButtonsView(View):
    def __init__(self, bot, temp_channel):
        super().__init__()
        self.bot = bot
        self.temp_channel = temp_channel
        self.control_message = None
        self.followup_view = None

        self.create_items()

    async def send_initial_message(self):
        embeds = [ChannelInfoEmbed(self.bot, self.temp_channel), ControlIconsEmbed()]
        self.control_message = await self.temp_channel.send("", embeds=embeds, view=self)

    def create_items(self):
        channel_state = self.bot.db.get_temp_channel_info(self.temp_channel.id).channel_state

        state_row = 3

        # Define buttons and their callbacks
        lock_button = discord.ui.Button(
            label="",
            emoji="🔒",
            style=discord.ButtonStyle.success if channel_state == ChannelState.LOCKED.value else discord.ButtonStyle.primary,
            row=state_row,
            # disabled=(channel_state == ChannelState.LOCKED.value)
        )

        hide_button = discord.ui.Button(
            label="",
            emoji="🙈",
            style=discord.ButtonStyle.success if channel_state == ChannelState.HIDDEN.value else discord.ButtonStyle.primary,
            row=state_row,
            # disabled=(channel_state == ChannelState.HIDDEN.value)
        )

        public_button = discord.ui.Button(
            label="",
            emoji="🌐",
            style=discord.ButtonStyle.success if channel_state == ChannelState.PUBLIC.value else discord.ButtonStyle.primary,
            row=state_row,
            # disabled=(channel_state == ChannelState.PUBLIC.value)
        )

        modify_button = discord.ui.Button(
            label="",
            emoji="🔧",
            style=discord.ButtonStyle.secondary,
            row=0
        )

        kick_button = discord.ui.Button(
            label="",
            emoji="👢",
            style=discord.ButtonStyle.secondary,
            row=0
        )

        clear_button = discord.ui.Button(
            label="",
            emoji="🧽",
            style=discord.ButtonStyle.danger,
            row=1
        )

        delete_button = discord.ui.Button(
            label="",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            row=1
        )

        give_button = discord.ui.Button(
            label="",
            emoji="🎁",
            style=discord.ButtonStyle.success,
            row=0
        )

        ban_button = discord.ui.Button(
            label="",
            emoji="🔨",
            style=discord.ButtonStyle.danger,
            row=1
        )

        banner_button = discord.ui.Button(
            label="- - - - - - - - - - - - - - - - - - - -",
            #emoji="",
            style=discord.ButtonStyle.secondary,
            row=2,
            disabled=True
        )

        lock_button.callback = self.lock_button_callback
        hide_button.callback = self.hide_button_callback
        public_button.callback = self.public_button_callback
        modify_button.callback = self.modify_button_callback
        kick_button.callback = self.kick_button_callback
        clear_button.callback = self.clear_button_callback
        delete_button.callback = self.delete_button_callback
        give_button.callback = self.give_button_callback
        ban_button.callback = self.ban_button_callback

        self.add_item(public_button)
        self.add_item(hide_button)
        self.add_item(lock_button)

        self.add_item(banner_button)

        self.add_item(modify_button)
        self.add_item(kick_button)
        self.add_item(give_button)

        self.add_item(clear_button)
        self.add_item(ban_button)
        self.add_item(delete_button)

    async def update(self):
        embeds = [ChannelInfoEmbed(self.bot, self.control_message.channel), ControlIconsEmbed()]
        self.clear_items()
        self.create_items()
        await self.control_message.edit(view=self, embeds=embeds)

    async def on_timeout(self):
        self.bot.logger.error("timed out", self.control_message)

    # --- Callbacks ---
    async def lock_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `lock`", ephemeral=True, delete_after=20)

    async def hide_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `hide`", ephemeral=True, delete_after=20)

    async def public_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `public`", ephemeral=True, delete_after=20)

    async def modify_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `modify`", ephemeral=True, delete_after=20)

    async def kick_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `kick`", ephemeral=True, delete_after=20)

    async def clear_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `clear`", ephemeral=True, delete_after=20)

    async def delete_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `delete`", ephemeral=True, delete_after=20)

    async def give_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `give`", ephemeral=True, delete_after=20)

    async def ban_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `ban`", ephemeral=True, delete_after=20)
