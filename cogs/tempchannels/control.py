import json
import os
import discord
from discord.ext import commands
import discord.ui
import databasecontrol
import error_handling
from enum import Enum
import asyncio

base_directory = os.getenv('BASE_DIR', os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(base_directory, 'config.json')
# Load the configuration from config.json
with open(config_path) as config_file:
    config = json.load(config_file)


class ChannelState(Enum):
    PUBLIC = 0
    LOCKED = 1
    HIDDEN = 2


async def create_info_embed(database: databasecontrol.Database, channel):
    embed = discord.Embed(title=f"#{channel.name}", color=discord.Color.blue())

    owner_id = database.get_owner_id(channel.id)
    if owner_id:
        owner = await channel.guild.fetch_member(owner_id)
        if owner is not None:
            owner = owner.mention
        else:
            owner = "None, available to claim"
    else:
        owner = "None, available to claim"
    embed.add_field(name="Owner", value=f"{owner}", inline=True)

    # limit = self.channel.user_limit
    # if limit == 0:
    #     limit = "♾️ Unlimited"
    # info_embed.add_field(name="Limit", value=f"{limit}", inline=True)
    #
    # region = self.channel.rtc_region
    # if region is None:
    #     region = "🌍 Automatic"
    # info_embed.add_field(name="Region", value=f"{region}", inline=True)

    channel_state_id = database.get_channel_state_id(channel.guild.id, channel.id)
    if channel_state_id == ChannelState.PUBLIC.value:
        channel_state = "🌐 Public"
    elif channel_state_id == ChannelState.LOCKED.value:
        channel_state = "🔒 Locked"
    elif channel_state_id == ChannelState.HIDDEN.value:
        channel_state = "🙈 Hidden"
    else:
        channel_state = "None"
    embed.add_field(name="Access", value=f"{channel_state}", inline=True)

    return embed


async def update_info_embed(database: databasecontrol.Database, channel):
    control_message = None
    async for message in channel.history(limit=1, oldest_first=True):
        control_message = message
    embeds = control_message.embeds
    embeds[0] = await create_info_embed(database, channel)
    await control_message.edit(embeds=embeds)


class KickControlView(discord.ui.View):
    """A view containing buttons and menus for managing channel creators."""

    def __init__(self, bot: commands.Bot, database: databasecontrol.Database, channel, is_ban: bool = False):
        super().__init__(timeout=60)
        self.bot = bot
        self.database = database
        self.channel = channel
        self.message = None

        self.add_item(KickSelectMenu(bot, self.database, self.channel, is_ban))

    async def send_initial_message(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="👟 Who would you like to kick from your channel?",
            description=f"You have 60 seconds to select at least one member.",
            color=0x00ff00
        )
        await interaction.response.defer()
        self.message = await interaction.followup.send(embed=embed, view=self, ephemeral=True, wait=True)  # wait ensures that self.message is set before continuing

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass


class KickSelectMenu(discord.ui.Select):
    """A dropdown menu for selecting users to kick."""

    def __init__(self, bot: commands.Bot, database: databasecontrol.Database, channel: discord.abc.GuildChannel, is_ban: bool = False):
        self.bot = bot
        self.database = database
        self.channel = channel
        self.is_ban = is_ban

        owner_id = database.get_owner_id(channel.id)

        options = []
        for member in channel.members:
            if member.id == owner_id:
                continue
            options.append(
                discord.SelectOption(
                    label=f"{member.display_name}",
                    description=f"",
                    value=f"{member.id}",
                    emoji="👥"
                )
            )

        if not options:
            options = [
                discord.SelectOption(
                    label="None",
                    value="None",
                    emoji="🔧",
                    description="No members to select"
                )
            ]
            super().__init__(placeholder="No members to select", options=options, disabled=True)
        else:
            super().__init__(placeholder="Select users to kick", options=options, min_values=1, max_values=len(options))

    async def callback(self, interaction: discord.Interaction):
        kick_perms = {'connect': False, 'view_channel': False}
        selected_members = self.values
        members = []
        for member_id in selected_members:
            member = interaction.guild.get_member(int(member_id))
            if member:
                members.append(member)
                await member.move_to(None)
                if self.is_ban:
                    await self.channel.set_permissions(
                        member,
                        **kick_perms
                    )

        if len(members) > 0:
            action = "Kicked"
            if self.is_ban:
                action = "Banned"
            embed = discord.Embed(
                title=f"{action}!",
                description=f"{action} {len(members)} member(s) from your channel.",
                color=0x00ff00
            )
            embed.set_footer(text="This message will disappear in 10 seconds.")
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)
            if self.view.message:
                await self.view.message.delete()


class GiveControlView(discord.ui.View):
    """A view containing a select menu to choose a user currently connected to the temp channel."""

    def __init__(self, bot: commands.Bot, database: databasecontrol.Database, channel):
        super().__init__(timeout=60)
        self.bot = bot
        self.database = database
        self.channel = channel
        self.message = None

        self.add_item(GiveSelectMenu(bot, self.database, self.channel))

    async def send_initial_message(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎁 Who would you like to give your channel to?",
            description=f"You have 60 seconds to select one member.",
            color=0x00ff00
        )
        await interaction.response.defer()
        self.message = await interaction.followup.send(embed=embed, view=self, ephemeral=True, wait=True)  # wait ensures that self.message is set before continuing

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass


class GiveSelectMenu(discord.ui.Select):
    """A dropdown menu for selecting users to kick."""

    def __init__(self, bot: commands.Bot, database: databasecontrol.Database, channel: discord.abc.GuildChannel):
        self.bot = bot
        self.database = database
        self.channel = channel

        owner_id = database.get_owner_id(channel.id)

        options = []
        for member in channel.members:
            if member.id == owner_id:
                continue
            options.append(
                discord.SelectOption(
                    label=f"{member.display_name}",
                    description=f"",
                    value=f"{member.id}",
                    emoji="👥"
                )
            )

        if not options:
            options = [
                discord.SelectOption(
                    label="None",
                    value="None",
                    emoji="🔧",
                    description="No members to select"
                )
            ]
            super().__init__(placeholder="No members to select", options=options, disabled=True)
        else:
            super().__init__(placeholder="Select user", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        owner_perms = {'connect': True, 'view_channel': True}
        selected_member = interaction.guild.get_member(int(self.values[0]))
        if selected_member:
            await self.channel.set_permissions(
                selected_member,
                **owner_perms
            )

            embed = discord.Embed(
                title="Transferred!",
                description=f"Ownership of your channel was successfully transferred to {selected_member.mention}.",
                color=0x00ff00
            )
            embed.set_footer(text="This message will disappear in 20 seconds.")
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)

            embed = discord.Embed(
                title="Channel Ownership",
                description=f"You now own this channel! Use the above buttons to manage it as you wish.",
                color=discord.Color.blue()
            )
            embed.set_footer(text="This message will disappear in 60 seconds.")
            await self.channel.send(f"{selected_member.mention}", embed=embed, delete_after=60)

            self.database.set_owner_id(self.channel.id, selected_member.id)

            if self.view.message:
                await self.view.message.delete()

            await update_info_embed(self.database, self.channel)


class FollowupView(discord.ui.View):
    """A view containing buttons and menus for managing channel permissions."""

    def __init__(self, bot: commands.Bot, database: databasecontrol.Database, channel):
        super().__init__(timeout=880)  # 880, 20 seconds before 15 minutes
        self.bot = bot
        self.database = database
        self.channel = channel
        self.message = None

        self.setup_items()

    def setup_items(self):
        allow_perms = {'connect': True, 'view_channel': True}
        ban_perms = {'connect': False, 'view_channel': False}

        channel_state = ChannelState(self.database.get_channel_state_id(self.channel.guild.id, self.channel.id))
        if channel_state == ChannelState.PUBLIC:
            self.add_item(UpdatePermSelectMenu(self.bot, self.database, self.channel, ban_perms, "Select a user or role to BAN"))
            self.add_item(RemoveOverwritesSelectMenu(self.bot, self.database, self.channel, ban_perms, "Remove user or role from BANLIST"))
        elif channel_state in (ChannelState.LOCKED, ChannelState.HIDDEN):
            self.add_item(UpdatePermSelectMenu(self.bot, self.database, self.channel, allow_perms, "Select a user or role to ALLOW"))
            self.add_item(RemoveOverwritesSelectMenu(self.bot, self.database, self.channel, allow_perms, "Remove user or role from ALLOWLIST"))

        refresh_button = discord.ui.Button(emoji="🔄", label="Refresh", style=discord.ButtonStyle.blurple, custom_id="refresh")
        refresh_button.callback = self.send_message
        self.add_item(refresh_button)

    async def send_message(self, interaction: discord.Interaction=None):
        # Defer the interaction if it's not already responded to
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

        # Separate members who can and can't connect
        can_connect = []
        cant_connect = []
        if self.channel.type == discord.ChannelType.voice:
            for member in self.channel.guild.members:
                if not member.bot:
                    permissions = self.channel.permissions_for(member)
                    if permissions.connect:
                        can_connect.append(member)
                    else:
                        cant_connect.append(member)

        channel_state = ChannelState(self.database.get_channel_state_id(self.channel.guild.id, self.channel.id))
        # Determine the channel state
        titles = {
            ChannelState.PUBLIC: "🌐 Your Channel is `PUBLIC`",
            ChannelState.LOCKED: "🔒 Your Channel is `LOCKED`",
            ChannelState.HIDDEN: "🙈 Your Channel is `HIDDEN`"
        }
        title = titles.get(channel_state, "Unknown")

        colours = {
            ChannelState.PUBLIC: 0x00ff00,  # green
            ChannelState.LOCKED: 0xFF0000,  # red
            ChannelState.HIDDEN: 0xFFA500  # orange
        }
        colour = colours.get(channel_state, 0x00ff00)  # green

        # Create the embed message
        embed = discord.Embed(
            title=title,
            color=colour
        )
        value = ",\n".join([member.mention for member in can_connect]) or "None"
        if len(value) > 1024:
            value = f"{len(can_connect)} members"
        embed.add_field(
            name="Allowed Users",
            value=value,
            inline=True
        )
        value = ",\n".join([member.mention for member in cant_connect]) or "None"
        if len(value) > 1024:
            value = f"{len(cant_connect)} members"
        embed.add_field(
            name="Blocked Users",
            value=value,
            inline=True
        )

        self.clear_items()
        self.setup_items()

        # use asyncio to run the tasks simultaneously
        tasks = []
        if self.message:
            tasks.append(self.message.delete())
        tasks.append(interaction.followup.send(embed=embed, view=self, ephemeral=True))
        results = await asyncio.gather(*tasks)
        self.message = results[-1]

        return self.message

    async def on_timeout(self):
        new_view = FollowupView(self.bot, self.database, self.channel)
        if self.message:
            await self.message.edit(view=new_view)
            new_view.message = self.message  # Attach the new view to the same message


class UpdatePermSelectMenu(discord.ui.MentionableSelect):
    """A dropdown menu for selecting users or roles to update permissions."""

    def __init__(self,
                 bot: commands.Bot,
                 database: databasecontrol.Database,
                 channel: discord.abc.GuildChannel,
                 permissions: dict,
                 placeholder: str
                 ):
        self.bot = bot
        self.database = database
        self.channel = channel
        self.permissions = permissions

        super().__init__(
            placeholder=placeholder,
            min_values=0,
            max_values=25
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle the selection of users or roles."""
        await interaction.response.defer()
        selected_entities = self.values  # The selected users or roles

        # Iterate through the selected users or roles
        for entity in selected_entities:
            # Check if the entity is a Member (user) or a Role
            member = interaction.guild.get_member(int(entity.id))
            if member:
                target = member
            else:
                # Fetch all roles and find the matching role by ID
                roles = await interaction.guild.fetch_roles()
                target = discord.utils.get(roles, id=int(entity.id))

            if target:
                # Update permissions for viewing and connecting
                await self.channel.set_permissions(
                    target,
                    **self.permissions
                )

        # Refresh the view
        await self.view.send_message(interaction)


class RemoveOverwritesSelectMenu(discord.ui.Select):
    """A dropdown menu for removing permission overwrites."""

    def __init__(self,
                 bot: commands.Bot,
                 database: databasecontrol.Database,
                 channel: discord.abc.GuildChannel,
                 permissions: dict,
                 placeholder: str
                 ):
        self.bot = bot
        self.database = database
        self.channel = channel
        self.permissions = permissions  # example: {'connect': False, 'view_channel': False}

        # Get all permission overwrites
        overwrites = channel.overwrites

        channel_owner_id = database.get_owner_id(channel.id)

        options = []
        for target, overwrite in overwrites.items():

            # Exclude the everyone role since it's managed by the main buttons
            if target.id == channel.guild.default_role.id or target.id == channel_owner_id:
                continue

            exclude_target = True
            for perm, expected_value in self.permissions.items():
                current_value = getattr(overwrite, perm, None)

                # If the permission matches, we should include this target
                if current_value == expected_value:
                    exclude_target = False
                    break

            if not exclude_target:
                # Check if target is a user (discord.Member) or a role (discord.Role)
                if isinstance(target, discord.Member):
                    emoji = "👤"
                    label = target.display_name
                elif isinstance(target, discord.Role):
                    emoji = "🔧"
                    label = target.name

                # Append the option with the appropriate emoji
                options.append(
                    discord.SelectOption(
                        label=f"{label}",
                        description=f"",
                        value=f"{target.id}",
                        emoji=emoji
                    )
                )

        if len(options) <= 0:
            options.append(
                discord.SelectOption(
                    label=f"None",
                    description=f"Don't select me",
                    value=f"None",
                    emoji="🔧"
                )
            )
            super().__init__(
                placeholder=placeholder,
                options=options,
                disabled=True,
                min_values=0,
                max_values=1
            )
        else:
            super().__init__(
                placeholder=placeholder,
                options=options,
                min_values=0,
                max_values=len(options)
            )

    async def callback(self, interaction: discord.Interaction):
        """Handle the selection of users or roles."""
        await interaction.response.defer()
        selected_entities = self.values  # The selected users or roles

        # Iterate through the selected users or roles
        for entity_id in selected_entities:
            # Check if the entity is a Member (user) or a Role
            member = interaction.guild.get_member(int(entity_id))
            if member:
                target = member
            else:
                # Fetch all roles and find the matching role by ID
                roles = await interaction.guild.fetch_roles()
                target = discord.utils.get(roles, id=int(entity_id))

            if target:
                # Remove permissions
                await self.channel.set_permissions(target, overwrite=None)

        # Refresh the view
        await self.view.send_message(interaction)


class CreateControlView(discord.ui.View):
    """A view containing buttons and menus for managing channel settings."""

    def __init__(self, bot: commands.Bot, database, channel):
        super().__init__(timeout=None)
        self.bot = bot
        self.database = database
        self.channel = channel
        self.message = None
        self.followup_view = None

        self.setup_items()

    def setup_items(self):
        channel_state = self.database.get_channel_state_id(self.channel.guild.id, self.channel.id)

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
        public_button.callback = self.public_button_callback

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

    async def send_initial_message(self, interaction: discord.Interaction=None):
        # First embed
        icons_embed = discord.Embed(
            title="",
            description="",
            color=0x00ff00
        )

        icons_embed.add_field(name="🔧 Modify", value="", inline=True)
        icons_embed.add_field(name="👢 Kick", value="", inline=True)
        icons_embed.add_field(name="🎁 Give/Claim", value="", inline=True)
        icons_embed.add_field(name="🧽 Clear", value="", inline=True)
        icons_embed.add_field(name="🔨 Ban", value="", inline=True)
        icons_embed.add_field(name="🗑️ Delete", value="", inline=True)
        icons_embed.add_field(name="🌐 Public", value="", inline=True)
        icons_embed.add_field(name="🙈 Hide", value="", inline=True)
        icons_embed.add_field(name="🔒 Lock", value="", inline=True)

        info_embed = await create_info_embed(self.database, self.channel)

        # Sending both embeds in a single message
        if interaction:
            await interaction.response.defer()
            self.message = await interaction.followup.send(embeds=[info_embed, icons_embed], view=self)
        else:
            self.message = await self.channel.send(embeds=[info_embed, icons_embed], view=self)

    async def modify_button_callback(self, interaction: discord.Interaction):
        if self.database.get_owner_id(interaction.channel.id) != interaction.user.id:
            return await error_handling.handle_channel_owner_error(interaction)

        modal = ModifyChannelModal(self.bot, self.database, interaction.channel)
        await interaction.response.send_modal(modal)

    async def kick_button_callback(self, interaction: discord.Interaction):
        if self.database.get_owner_id(interaction.channel.id) != interaction.user.id:
            return await error_handling.handle_channel_owner_error(interaction)

        await KickControlView(self.bot, self.database, interaction.channel, is_ban=False).send_initial_message(interaction)

    async def clear_button_callback(self, interaction: discord.Interaction):
        if self.database.get_owner_id(interaction.channel.id) != interaction.user.id:
            return await error_handling.handle_channel_owner_error(interaction)
        await interaction.response.defer(ephemeral=True)

        excluded_message_ids = []
        if interaction.message:
            excluded_message_ids.append(interaction.message.id)
        if self.followup_view and self.followup_view.message:
            excluded_message_ids.append(self.followup_view.message.id)

        # Fetch messages from the channel
        messages_to_delete = []
        async for message in interaction.channel.history(limit=None):
            if message.id not in excluded_message_ids:
                messages_to_delete.append(message)

        # Bulk delete the filtered messages
        if messages_to_delete:
            await interaction.channel.delete_messages(messages_to_delete)

        embed = discord.Embed(
            title="Messages Deleted",
            description=f"Deleted {len(messages_to_delete)} messages.",
            color=discord.Color.red()
        )
        embed.set_footer(text="This message will disappear in 10 seconds.")
        message = await interaction.followup.send(embed=embed, ephemeral=True)
        await asyncio.sleep(10)
        await message.delete()

    async def delete_button_callback(self, interaction: discord.Interaction):
        if self.database.get_owner_id(interaction.channel.id) != interaction.user.id:
            return await error_handling.handle_channel_owner_error(interaction)

        # Ask for confirmation
        embed = discord.Embed(
            title="Channel Deletion Confirmation",
            description="Are you sure you want to delete this channel? Reply with 'yes' within 60 seconds to confirm.",
            color=discord.Color.orange()  # You can adjust the color as needed
        )
        embed.set_footer(text="Awaiting your response...")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        def check(message: discord.Message):
            # Check that the message is from the same user in the same channel and contains 'yes'
            return message.author == interaction.user and message.channel == interaction.channel and message.content.lower() == "yes"

        try:
            # Wait for the user to respond with "yes" within 60 seconds
            confirmation_message = await self.bot.wait_for("message", check=check, timeout=60)

            # Delete the channel from the database and then delete the channel
            try:
                await interaction.channel.delete()
            except discord.Forbidden:
                return await error_handling.handle_bot_permission_error("manage_channels", interaction=interaction)
            except Exception as e:
                return await error_handling.handle_global_error("control_tempchannels", e)
            self.database.delete_temp_channel(interaction.channel.id)
        except asyncio.TimeoutError:
            try:
                # If the user does not respond in time, send a timeout message
                embed = discord.Embed(
                    title="Channel Deletion Timed Out",
                    description="Channel deletion timed out. No action was taken.",
                    color=discord.Color.red()
                )
                embed.set_footer(text="This message will disappear in 10 seconds.")
                await interaction.followup.send(embed=embed, ephemeral=True, delete_after=10)
            except e:
                pass

    async def give_button_callback(self, interaction: discord.Interaction):
        owner_id = self.database.get_owner_id(interaction.channel.id)

        if owner_id is not None and owner_id != interaction.user.id:
            owner = await interaction.guild.fetch_member(owner_id)
            embed = discord.Embed(
                title="Ownership Notice",
                description=f"This channel is already owned by {owner.mention}.",
                color=discord.Color.orange()  # You can change the color to your preference
            )
            embed.set_footer(text="This message will disappear in 10 seconds.")
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)

        elif interaction.user not in interaction.channel.members:
            embed = discord.Embed(
                title="Action Required",
                description="You must be connected to this channel to claim it.",
                color=discord.Color.yellow()
            )
            embed.set_footer(text="This message will disappear in 10 seconds.")
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)

        elif owner_id is None and interaction.user in interaction.channel.members:
            self.database.set_owner_id(interaction.channel.id, interaction.user.id)
            embed = discord.Embed(
                title="Channel Claimed!",
                description="You have successfully claimed this channel!",
                color=discord.Color.green()
            )
            embed.set_footer(text="This message will disappear in 20 seconds.")
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)

            await update_info_embed(self.database, interaction.channel)

        elif owner_id:
            await GiveControlView(self.bot, self.database, interaction.channel).send_initial_message(interaction)

    async def ban_button_callback(self, interaction: discord.Interaction):
        if self.database.get_owner_id(interaction.channel.id) != interaction.user.id:
            return await error_handling.handle_channel_owner_error(interaction)

        await KickControlView(self.bot, self.database, interaction.channel, is_ban=True).send_initial_message(interaction)

    async def lock_button_callback(self, interaction: discord.Interaction):
        await self.update_channel(
            interaction,
            ChannelState.LOCKED,
        )

    async def hide_button_callback(self, interaction: discord.Interaction):
        await self.update_channel(
            interaction,
            ChannelState.HIDDEN,
        )

    async def public_button_callback(self, interaction: discord.Interaction):
        await self.update_channel(
            interaction,
            ChannelState.PUBLIC,
        )

    async def update_channel(self, interaction, new_state: ChannelState):
        if self.database.get_owner_id(interaction.channel.id) != interaction.user.id:
            return await error_handling.handle_channel_owner_error(interaction)

        await interaction.response.defer()

        if new_state == ChannelState.PUBLIC:
            permissions = {'connect': True, 'view_channel': True}
        elif new_state == ChannelState.LOCKED:
            permissions = {'connect': False, 'view_channel': True}
        elif new_state == ChannelState.HIDDEN:
            permissions = {'view_channel': False}
        else:
            await error_handling.handle_global_error("Unexpected channel state")
            return

        # Set permissions and channel_state in database
        connected_users = [member for member in interaction.channel.members if not member.bot]
        for user in connected_users:
            await interaction.channel.set_permissions(user, connect=True, view_channel=True)
        await interaction.channel.set_permissions(interaction.guild.default_role, **permissions)
        self.database.update_channel_state(interaction.channel.guild.id, interaction.channel.id, new_state.value)

        # Update the control menu
        self.clear_items()
        self.setup_items()
        await self.message.edit(view=self)

        # Create or update followup message
        if not self.followup_view:
            self.followup_view = FollowupView(
                bot=self.bot,
                database=self.database,
                channel=interaction.channel,
            )
        await self.followup_view.send_message(interaction)

        await update_info_embed(self.database, interaction.channel)


class ModifyChannelModal(discord.ui.Modal, title="Edit Your Channel"):
    def __init__(self, bot: commands.Bot, database: databasecontrol.Database, channel):
        super().__init__()
        self.bot = bot
        self.database = database
        self.channel = channel

        # Define the text inputs
        self.channel_name = discord.ui.TextInput(
            label="Channel Name",
            placeholder=f"{channel.name}",
            required=False,
            max_length=25
        )
        self.user_limit = discord.ui.TextInput(
            label="User Limit (Unlimited = 0)",
            placeholder=f"{channel.user_limit}",
            required=False,
            max_length=2
        )

        self.add_item(self.channel_name)
        self.add_item(self.user_limit)

    async def on_submit(self, interaction: discord.Interaction):
        # Update the channel
        channel_name = self.channel_name.value or self.channel.name
        user_limit = self.user_limit.value or str(self.channel.user_limit)

        if not user_limit.isnumeric():
            embed = discord.Embed(
                title="Invalid Input",
                description="User limit must be a number.",
                color=discord.Color.red()
            )
            embed.set_footer(text="This message will disappear in 20 seconds.")
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
            return

        await self.channel.edit(name=channel_name, user_limit=int(user_limit))
        embed = discord.Embed(
            title="Channel Updated",
            description="Your channel has been updated.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="This message will disappear in 10 seconds.")
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)


class ControlTempChannelsCog(commands.Cog):
    def __init__(self, bot: commands.Bot, database):
        self.bot = bot
        self.database = database
        self.last_followup_message_id = None


async def setup(bot: commands.Bot, database):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(ControlTempChannelsCog(bot, database))
