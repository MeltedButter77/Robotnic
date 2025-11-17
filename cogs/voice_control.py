import asyncio
import json
from discord.ui import View, Select, Button, Modal, InputText
from enum import Enum
import discord
from discord.ext import commands
from pathlib import Path

script_dir = Path(__file__).parent
settings_path = script_dir / "../settings.json"

# Load settings
with open(settings_path, "r") as f:
    settings = json.load(f)
labeled_icons = settings["control_message"].get("labeled_icons", True)
icon_description_embed = settings["control_message"].get("icon_description_embed", False)


class VoiceControlCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(VoiceControlCog(bot))


class ChannelState(Enum):
    PUBLIC = 0
    LOCKED = 1
    HIDDEN = 2


async def update_info_embed(bot, channel, title=None, user_limit=None):
    control_message = None
    async for message in channel.history(limit=1, oldest_first=True):
        control_message = message
    if control_message is None:
        print("Failed to find control message")
        return
    embeds = control_message.embeds
    embeds[0] = ChannelInfoEmbed(bot, channel, title, user_limit)
    await control_message.edit(embeds=embeds)


class ControlIconsEmbed(discord.Embed):
    def __init__(self):
        super().__init__(
            title="",
            description="",
            color=0x00ff00
        )

        self.add_field(name="🏷️ Rename", value="", inline=True)
        self.add_field(name="🚧 Limit", value="", inline=True)
        self.add_field(name="🎁 Give", value="", inline=True)
        self.add_field(name="🧽 Clear", value="", inline=True)
        self.add_field(name="🔨 Ban", value="", inline=True)
        self.add_field(name="🗑️ Delete", value="", inline=True)
        # self.add_field(name="🌐 Public", value="", inline=True)
        # self.add_field(name="🙈 Hide", value="", inline=True)
        # self.add_field(name="🔒 Lock", value="", inline=True)


class ChannelInfoEmbed(discord.Embed):
    def __init__(self, bot, temp_channel, title=None, user_limit=None):
        super().__init__(
            color=discord.Color.blue()
        )

        # title input incase it was just changed and propagated to channel yet
        self.title = title
        if not self.title:
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

        if not user_limit:
            user_limit = temp_channel.user_limit
        if user_limit == 0:
            user_limit = "♾️ Unlimited"
        self.add_field(name="User Limit", value=f"{user_limit}", inline=True)

        # region = temp_channel.rtc_region
        # if region is None:
        #     region = "🌍 Auto"
        # self.add_field(name="Region", value=f"{region}", inline=True)

        # channel_state_id = temp_channel_info.channel_state
        # if channel_state_id == ChannelState.PUBLIC.value:
        #     channel_state = "🌐 Public"
        # elif channel_state_id == ChannelState.LOCKED.value:
        #     channel_state = "🔒 Locked"
        # elif channel_state_id == ChannelState.HIDDEN.value:
        #     channel_state = "🙈 Hidden"
        # else:
        #     channel_state = "None"
        # self.add_field(name="Access", value=f"{channel_state}", inline=True)


class ButtonsView(View):
    def __init__(self, bot, temp_channel):
        super().__init__(timeout=None)
        self.bot = bot
        self.temp_channel = temp_channel
        self.control_message = None
        self.followup_view = None

        self.create_items()

    async def send_initial_message(self):
        embeds = [ChannelInfoEmbed(self.bot, self.temp_channel)]
        if icon_description_embed:
            embed = ControlIconsEmbed()
            embeds.append(embed)
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

        name_button = discord.ui.Button(
            label="",
            emoji="🏷️",
            style=discord.ButtonStyle.secondary,
            row=0
        )

        limit_button = discord.ui.Button(
            label="",
            emoji="🚧",
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

        if labeled_icons:
            lock_button.label = "Lock"
            hide_button.label = "Hide"
            public_button.label = "Public"
            name_button.label = "Rename"
            limit_button.label = "Edit Limit"
            clear_button.label = "Clear Msgs"
            delete_button.label = "Delete"
            give_button.label = "Give/Claim"
            ban_button.label = "Ban User"

        lock_button.callback = self.lock_button_callback
        hide_button.callback = self.hide_button_callback
        public_button.callback = self.public_button_callback
        name_button.callback = self.name_button_callback
        limit_button.callback = self.limit_button_callback
        clear_button.callback = self.clear_button_callback
        delete_button.callback = self.delete_button_callback
        give_button.callback = self.give_button_callback
        ban_button.callback = self.ban_button_callback

        # self.add_item(public_button)
        # self.add_item(hide_button)
        # self.add_item(lock_button)
        #
        # self.add_item(banner_button)

        self.add_item(name_button)
        self.add_item(limit_button)
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
        self.bot.logger.error(f"Control message timed out in {self.control_message.channel.name}")
        self.clear_items()
        self.add_item(
            discord.ui.Button(
                label="This control message has expired",
                style=discord.ButtonStyle.secondary,
                disabled=True
            )
        )
        # Edit the message to show the new view
        try:
            await self.control_message.edit(view=self)
        except Exception as e:
            self.bot.logger.debug(f"Failed to update control message after timeout. Handled. {e}")

    # --- Callbacks ---
    async def lock_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `lock`", ephemeral=True, delete_after=20)

    async def hide_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `hide`", ephemeral=True, delete_after=20)

    async def public_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `public`", ephemeral=True, delete_after=20)

    async def name_button_callback(self, interaction: discord.Interaction):
        if self.bot.db.get_temp_channel_info(interaction.channel.id).owner_id != interaction.user.id:
            self.bot.logger.debug(f"User ({interaction.user}) interacted with control message that they don't own.")
            return await interaction.response.send_message(f"You do not own this temporary channel {interaction.user.mention}!", ephemeral=True, delete_after=15)

        modal = ChangeNameModal(self.bot, interaction.channel)
        await interaction.response.send_modal(modal)

    async def limit_button_callback(self, interaction: discord.Interaction):
        if self.bot.db.get_temp_channel_info(interaction.channel.id).owner_id != interaction.user.id:
            self.bot.logger.debug(f"User ({interaction.user}) interacted with control message that they don't own.")
            return await interaction.response.send_message(f"You do not own this temporary channel {interaction.user.mention}!", ephemeral=True, delete_after=15)

        modal = UserLimitModal(self.bot, interaction.channel)
        await interaction.response.send_modal(modal)

    async def clear_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if self.bot.db.get_temp_channel_info(interaction.channel.id).owner_id != interaction.user.id:
            self.bot.logger.debug(f"User ({interaction.user}) interacted with control message that they don't own.")
            return await interaction.followup.send(f"You do not own this temporary channel {interaction.user.mention}!", ephemeral=True, delete_after=15)

        excluded_message_ids = []
        if interaction.message:
            excluded_message_ids.append(interaction.message.id)
        if self.followup_view and self.followup_view.control_message:
            excluded_message_ids.append(self.followup_view.control_message.id)

        # Fetch messages from the channel
        messages_to_delete = []
        async for message in interaction.channel.history(limit=None):
            if message.id not in excluded_message_ids:
                messages_to_delete.append(message)

        # Bulk delete the filtered messages
        if messages_to_delete:
            try:
                await interaction.channel.delete_messages(messages_to_delete)
            except Exception as e:
                await interaction.followup.send(f"Failed, {e}", ephemeral=True, delete_after=15)

        embed = discord.Embed(
            title="Messages Deleted",
            description=f"Deleted `{len(messages_to_delete)}` messages.",
            color=discord.Color.red()
        )
        embed.set_footer(text="This message will disappear in 15 seconds.")
        await interaction.followup.send(embed=embed, ephemeral=True, delete_after=15)

    async def delete_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if self.bot.db.get_temp_channel_info(interaction.channel.id).owner_id != interaction.user.id:
            self.bot.logger.debug(f"User ({interaction.user}) interacted with control message that they don't own.")
            return await interaction.followup.send(f"You do not own this temporary channel {interaction.user.mention}!", ephemeral=True, delete_after=15)

        # Ask for confirmation
        embed = discord.Embed(
            title="Channel Deletion Confirmation",
            description="Are you sure you want to delete this channel? Reply with 'yes' within 60 seconds to confirm.",
            color=discord.Color.orange()  # You can adjust the color as needed
        )
        embed.set_footer(text="Awaiting your response...")
        await interaction.followup.send(embed=embed, ephemeral=True, delete_after=60)

        def check(message: discord.Message):
            # Check that the message is from the same user in the same channel and contains 'yes'
            return message.author == interaction.user and message.channel == interaction.channel and message.content.lower() == "yes"

        try:
            # Wait for the user to respond with "yes" within 60 seconds
            confirmation_message = await self.bot.wait_for("message", check=check, timeout=60)

            # Delete the channel from the database and then delete the channel
            try:
                await interaction.channel.delete()
            except Exception as e:
                self.bot.logger.error(f"error deleting channel, {interaction}")
                raise

            try:
                await interaction.channel.delete()
            except discord.NotFound as e:
                self.bot.logger.debug(f"Channel not found removing temp channel, handled. {e}")
            except discord.Forbidden as e:
                self.bot.logger.debug(f"Permission error removing temp channel, handled by sending a message notifying of lack of perms. {e}")
                await interaction.channel.send(f"Sorry {interaction.user.mention}, I do not have permission to delete this channel.", delete_after=300)
                return
            except Exception as e:
                self.bot.logger.error(f"Unknown error removing temp channel, handled. {e}")

            self.bot.db.remove_temp_channel(interaction.channel.id)
        except asyncio.TimeoutError:
            try:
                # If the user does not respond in time, send a timeout message
                embed = discord.Embed(
                    title="Channel Deletion Timed Out",
                    description="Channel deletion timed out. No action was taken.",
                    color=discord.Color.red()
                )
                embed.set_footer(text="This message will disappear in 15 seconds.")
                await interaction.followup.send(embed=embed, ephemeral=True, delete_after=15)
            except e:
                pass

    async def give_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `give`", ephemeral=True, delete_after=20)

    async def ban_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `ban`", ephemeral=True, delete_after=20)


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
            await self.bot.renamer.schedule_name_update(self.channel, channel_name)
            await update_info_embed(self.bot, self.channel, title=channel_name)
            self.bot.db.set_temp_channel_is_renamed(self.channel.id, True)
        else:
            self.bot.db.set_temp_channel_is_renamed(self.channel.id, False)
            # Should trigger Channel name and control embed updates. currently handled by coroutine.

        embed = discord.Embed(
            title="Changes Saved",
            description="Your channel will update as soon as possible. Sometimes Discord will limit updates if they are too frequent, please be patient.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="This message will disappear in 30 seconds.")
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=30)


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
