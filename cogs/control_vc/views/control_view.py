import asyncio
import discord
from discord.ui import View
from cogs.control_vc.enums import ChannelState
from cogs.control_vc.embeds import ChannelInfoEmbed, ControlIconsEmbed
from cogs.control_vc.owner import is_owner
from cogs.control_vc.modals import UserLimitModal, ChangeNameModal
from cogs.control_vc.views.give_ownership import GiveOwnershipView
from cogs.control_vc.views.ban_user import BanUserView


class ControlView(View):
    def __init__(self, bot, temp_channel):
        super().__init__(timeout=None)
        self.bot = bot
        self.temp_channel = temp_channel
        self.control_message = None

        self.create_items()

    async def send_initial_message(self, owner_member, channel_name=None):
        embed = discord.Embed(color=discord.Color.green())
        embed.description = f"This is a [FOSS](<https://wikipedia.org/wiki/Free_and_open-source_software>) project developed by [MeltedButter77](<https://github.com/MeltedButter77>).\nYou can contribute [here](<https://github.com/MeltedButter77/Robotnic>) or support it [here](<https://github.com/sponsors/MeltedButter77>)."
        embeds = [
            embed,
            ChannelInfoEmbed(self.bot, self.temp_channel, title=channel_name)
        ]
        if self.bot.settings["control_message"].get("buttons_description_embed", True):
            embeds.append(ControlIconsEmbed(self.bot))

        is_mention_owner = self.bot.repos.guild_settings.get(self.temp_channel.guild.id)["mention_owner_bool"]

        self.control_message = await self.temp_channel.send( embeds=embeds, view=self)

        if is_mention_owner:
            await self.temp_channel.send(f"Hey {owner_member.mention}, this is *your* vc. Use the message above to control it.", delete_after=10)


    def create_items(self):
        channel_state = self.bot.repos.temp_channels.get_info(self.temp_channel.id).channel_state

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

        if self.bot.settings["control_message"].get("button_labels", True):
            lock_button.label = "Lock"
            hide_button.label = "Hide"
            public_button.label = "Public"
            name_button.label = "Rename"
            limit_button.label = "Edit Limit"
            clear_button.label = "Clear Msgs"
            delete_button.label = "Delete"
            give_button.label = "Give"
            ban_button.label = "Ban User"

        guild_settings = self.bot.repos.guild_settings.get(self.temp_channel.guild.id)
        enabled_controls = guild_settings["enabled_controls"]

        if not self.bot.settings["control_message"].get("use_dropdown_instead_of_buttons", True):
            if "rename" in enabled_controls:
                self.add_item(name_button)
            if "limit" in enabled_controls:
                self.add_item(limit_button)
            if "clear" in enabled_controls:
                self.add_item(clear_button)
            if "ban" in enabled_controls:
                self.add_item(delete_button)
            if "give" in enabled_controls:
                self.add_item(give_button)
            if "delete" in enabled_controls:
                self.add_item(ban_button)
            if self.bot.settings["control_message"].get("state_changeable", False):
                self.add_item(banner_button)

        if self.bot.settings["control_message"].get("state_changeable", False):
            self.add_item(public_button)
            self.add_item(lock_button)
            self.add_item(hide_button)

        public_button.callback = self.public_button_callback
        lock_button.callback = self.lock_button_callback
        hide_button.callback = self.hide_button_callback
        name_button.callback = self.name_button_callback
        limit_button.callback = self.limit_button_callback
        clear_button.callback = self.clear_button_callback
        delete_button.callback = self.delete_button_callback
        give_button.callback = self.give_button_callback
        ban_button.callback = self.ban_button_callback

        if self.bot.settings["control_message"].get("use_dropdown_instead_of_buttons", True):
            class ActionDropdown(discord.ui.Select):
                def __init__(select_self):
                    options = []

                    if "rename" in enabled_controls:
                        options.append(discord.SelectOption(value="rename", label="Rename Channel", emoji="🏷️"))
                    if "limit" in enabled_controls:
                        options.append(discord.SelectOption(value="limit", label="Edit User Limit", emoji="🚧"))
                    if "clear" in enabled_controls:
                        options.append(discord.SelectOption(value="clear", label="Clear Messages", emoji="🧽"))
                    if "ban" in enabled_controls:
                        options.append(discord.SelectOption(value="ban", label="Ban Users or Roles", emoji="🔨"))
                    if "give" in enabled_controls:
                        options.append(discord.SelectOption(value="give", label="Give Ownership", emoji="🎁"))
                    if "delete" in enabled_controls:
                        options.append(discord.SelectOption(value="delete", label="Delete Channel", emoji="🗑️"))


                    super().__init__(
                        placeholder="Channel Actions…",
                        min_values=1,
                        max_values=1,
                        options=options,
                        row=0
                    )

                async def callback(select_self, interaction: discord.Interaction):
                    choice = select_self.values[0]

                    if choice == "rename":
                        await self.name_button_callback(interaction)
                    elif choice == "limit":
                        await self.limit_button_callback(interaction)
                    elif choice == "give":
                        await self.give_button_callback(interaction)
                    elif choice == "clear":
                        await self.clear_button_callback(interaction)
                    elif choice == "ban":
                        await self.ban_button_callback(interaction)
                    elif choice == "delete":
                        await self.delete_button_callback(interaction)

                    await self.update_view()  # Clears selected option of dropdown

            self.add_item(ActionDropdown())

    async def update_view(self):
        self.clear_items()
        self.create_items()
        await self.control_message.edit(view=self, embeds=self.control_message.embeds)

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
        await interaction.response.send_message("You selected `lock`. This is currently a WIP.", ephemeral=True, delete_after=20)

    async def hide_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `hide`. This is currently a WIP.", ephemeral=True, delete_after=20)

    async def public_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("You selected `public`. This is currently a WIP.", ephemeral=True, delete_after=20)

    async def name_button_callback(self, interaction: discord.Interaction):
        if not await is_owner(self, interaction):
            return
        modal = ChangeNameModal(self.bot, interaction.channel)
        await interaction.response.send_modal(modal)

    async def limit_button_callback(self, interaction: discord.Interaction):
        if not await is_owner(self, interaction):
            return
        modal = UserLimitModal(self.bot, interaction.channel)
        await interaction.response.send_modal(modal)

    async def clear_button_callback(self, interaction: discord.Interaction):
        if not await is_owner(self, interaction):
            return
        await interaction.response.defer(ephemeral=True)

        excluded_message_ids = []
        if interaction.message:
            excluded_message_ids.append(interaction.message.id)

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
        if not await is_owner(self, interaction):
            return
        await interaction.response.defer(ephemeral=True)

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

            self.bot.repos.temp_channels.remove(interaction.channel.id)
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
        if not await is_owner(self, interaction):
            return
        await interaction.response.defer(ephemeral=True)

        await GiveOwnershipView(self.bot, interaction.channel).send_initial_message(interaction)

    async def ban_button_callback(self, interaction: discord.Interaction):
        if not await is_owner(self, interaction):
            return
        await interaction.response.defer(ephemeral=True)

        await BanUserView(self.bot, interaction.channel).send_initial_message(interaction)

