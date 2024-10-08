import asyncio
import json
import os
import discord
from discord import app_commands
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

# TODO:
#  1. Migrate all view's to be initialised like the KickControlView
#  2. Add a button to give the channel to another user


class KickControlView(discord.ui.View):
    """A view containing buttons and menus for managing channel creators."""

    def __init__(self, bot: commands.Bot, database: databasecontrol.Database, channel):
        super().__init__(timeout=60)
        self.bot = bot
        self.database = database
        self.channel = channel
        self.message = None

        self.add_item(KickSelectMenu(bot, self.database, self.channel))

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
                    description="No members to kick"
                )
            ]
            super().__init__(placeholder="No members to kick", options=options, disabled=True)
        else:
            super().__init__(placeholder="Select users to kick", options=options, min_values=1, max_values=len(options))

    async def callback(self, interaction: discord.Interaction):
        kick_perms = {'connect': False, 'view_channel': False}
        selected_members = self.values
        members = []
        print(selected_members)
        for member_id in selected_members:
            member = interaction.guild.get_member(int(member_id))
            if member:
                members.append(member)
                await member.move_to(None)
                await self.channel.set_permissions(
                    member,
                    **kick_perms
                )

        if len(members) > 0:
            embed = discord.Embed(
                title="Kicked!",
                description=f"Kicked {len(members)} member(s) from your channel.",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            if self.view.message:
                await self.view.message.delete()
            await asyncio.sleep(10)
            await interaction.delete_original_response()


async def create_followup_menu(bot: commands.Bot, database: databasecontrol.Database, channel: discord.abc.GuildChannel, followup_id=None):
    """Updates the follow-up message in the channel."""
    channel_state = ChannelState(database.get_channel_state(channel.guild.id, channel.id))

    view = FollowupView(
        bot=bot,
        database=database,
        channel=channel,
        channel_state=channel_state,
        followup_id=followup_id
    )

    # Separate members who can and can't connect
    can_connect = []
    cant_connect = []
    if channel.type == discord.ChannelType.voice:
        for member in channel.guild.members:
            if not member.bot:
                permissions = channel.permissions_for(member)
                if permissions.connect:
                    can_connect.append(member)
                else:
                    cant_connect.append(member)

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

    text = ""
    return text, view, embed


class FollowupView(discord.ui.View):
    """A view containing buttons and menus for managing channel creators."""

    def __init__(self, bot: commands.Bot, database: databasecontrol.Database, channel, channel_state, followup_id=0):
        super().__init__(timeout=None)
        self.bot = bot
        self.database = database
        self.channel = channel
        self.channel_state = channel_state

        allow_perms = {'connect': True, 'view_channel': True}
        ban_perms = {'connect': False, 'view_channel': False}
        if channel_state == ChannelState.PUBLIC:
            self.add_item(UpdatePermSelectMenu(bot, self.database, ban_perms, "Select a user or role to BAN"))
            self.add_item(RemoveOverwritesSelectMenu(bot, self.database, channel, allow_perms, f"Remove user or role from BANLIST"))
        elif channel_state == ChannelState.LOCKED or channel_state == ChannelState.HIDDEN:
            self.add_item(UpdatePermSelectMenu(bot, self.database, allow_perms, "Select a user or role to ALLOW"))
            self.add_item(RemoveOverwritesSelectMenu(bot, self.database, channel, ban_perms, f"Remove user or role from ALLOWLIST"))


class UpdatePermSelectMenu(discord.ui.MentionableSelect):
    """A dropdown menu for selecting users or roles to give view and connect permissions to."""

    def __init__(self,
                 bot: commands.Bot,
                 database: databasecontrol.Database,
                 permissions: dict,
                 placeholder: str
                 ):
        self.bot = bot
        self.database = database
        self.permissions = permissions

        if permissions['connect']:
            super().__init__(
                placeholder=placeholder,
                min_values=0,
                max_values=25
            )
        else:
            super().__init__(
                placeholder="Select a user or role to BLOCK",
                min_values=0,
                max_values=25
            )

    async def callback(self, interaction: discord.Interaction):
        """Handle the selection of users or roles."""
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
                await interaction.channel.set_permissions(
                    target,
                    **self.permissions
                )

        text, view, embed = await create_followup_menu(self.bot, self.database, interaction.channel)
        await interaction.response.edit_message(content=text, embed=embed, view=None)
        await interaction.edit_original_response(content=text, embed=embed, view=view)


class RemoveOverwritesSelectMenu(discord.ui.Select):
    """A dropdown menu for selecting users or roles to give view and connect permissions to."""

    def __init__(self,
                 bot: commands.Bot,
                 database: databasecontrol.Database,
                 channel: discord.abc.GuildChannel,
                 permissions: dict,
                 placeholder: str
                 ):
        self.bot = bot
        self.database = database
        self.permissions = permissions # example: {'connect': False, 'view_channel': False}

        # Get all permission overwrites
        overwrites = channel.overwrites

        channel_owner_id = database.get_owner_id(channel.id)

        options = []
        for target, overwrite in overwrites.items():

            exclude_target = True
            for perm, expected_value in self.permissions.items():
                current_value = getattr(overwrite, perm, None)

                # Exclude the everyone role since its managed by the main buttons
                if target.id == channel.guild.default_role.id or target.id == channel_owner_id:
                    continue

                # If the permission does not match, we should include this target
                if current_value != expected_value:
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
                    description=f"Dont select me",
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
                # Update permissions for viewing and connecting
                await interaction.channel.set_permissions(target, overwrite=None)

        text, view, embed = await create_followup_menu(self.bot, self.database, interaction.channel)
        await interaction.response.edit_message(content=text, embed=embed, view=None)
        await interaction.edit_original_response(content=text, embed=embed, view=view)


async def create_control_menu(bot: commands.Bot, database: databasecontrol.Database, channel: discord.TextChannel, last_followup_message_id=None):
    view = CreateControlView(
        database=database,
        bot=bot,
        channel=channel,
        last_followup_message_id=last_followup_message_id,
    )

    embed = discord.Embed(
        title="Manage your Temporary Channel",
        description=f"Use the buttons below to manage your temporary channel.",
        color=0x00ff00
    )
    return view, embed


class CreateControlView(discord.ui.View):
    """A view containing buttons and menus for managing channel creators."""

    def __init__(self, database, bot: commands.Bot, channel, last_followup_message_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.database = database
        self.last_followup_message_id = last_followup_message_id

        channel_state = self.database.get_channel_state(channel.guild.id, channel.id)

        if channel_state != ChannelState.LOCKED.value:
            lock_button = discord.ui.Button(
                label="Lock",
                emoji="🔒",
                style=discord.ButtonStyle.primary,
                row=1
            )
        else:
            lock_button = discord.ui.Button(
                label="Lock",
                emoji="🔒",
                style=discord.ButtonStyle.primary,
                disabled=True,
                row=1
            )
        lock_button.callback = self.lock_button_callback

        if channel_state != ChannelState.HIDDEN.value:
            hide_button = discord.ui.Button(
                label="Hide",
                emoji="🙈",
                style=discord.ButtonStyle.primary,
                row=1
            )
        else:
            hide_button = discord.ui.Button(
                label="Hide",
                emoji="🙈",
                style=discord.ButtonStyle.primary,
                disabled=True,
                row=1
            )
        hide_button.callback = self.hide_button_callback

        if channel_state != ChannelState.PUBLIC.value:
            public_button = discord.ui.Button(
                label="Public",
                emoji="🌐",
                style=discord.ButtonStyle.primary,
                row=1
            )
        else:
            public_button = discord.ui.Button(
                label="Public",
                emoji="🌐",
                style=discord.ButtonStyle.primary,
                disabled=True,
                row=1
            )
        public_button.callback = self.public_button_callback

        refresh_button = discord.ui.Button(
            label="Refresh",
            emoji="🔄",
            style=discord.ButtonStyle.secondary,
            row=1
        )
        refresh_button.callback = self.refresh_button_callback

        modify_button = discord.ui.Button(
            label="Modify",
            emoji="🔧",
            style=discord.ButtonStyle.secondary
        )
        modify_button.callback = self.modify_button_callback

        kick_button = discord.ui.Button(
            label="Kick",
            emoji="👢",
            style=discord.ButtonStyle.secondary
        )
        kick_button.callback = self.kick_button_callback

        clear_button = discord.ui.Button(
            label="Clear Channel Messages",
            emoji="🎫",
            style=discord.ButtonStyle.danger,
            row=0
        )
        clear_button.callback = self.clear_button_callback

        give_button = discord.ui.Button(
            label="Give Channel",
            emoji="🎁",
            style=discord.ButtonStyle.success,
            row=2
        )
        give_button.callback = self.give_button_callback

        claim_button = discord.ui.Button(
            label="Claim Channel",
            emoji="🎫",
            style=discord.ButtonStyle.success,
            row=2
        )
        claim_button.callback = self.claim_button_callback

        delete_button = discord.ui.Button(
            label="Delete",
            emoji="🚫",
            style=discord.ButtonStyle.secondary,
            row=2
        )
        delete_button.callback = self.delete_button_callback

        self.add_item(modify_button)
        self.add_item(kick_button)
        self.add_item(clear_button)
        self.add_item(public_button)
        self.add_item(hide_button)
        self.add_item(lock_button)
        self.add_item(refresh_button)
        self.add_item(give_button)
        self.add_item(claim_button)
        self.add_item(delete_button)

    async def refresh_button_callback(self, interaction: discord.Interaction):
        channel_state_id = self.database.get_channel_state(interaction.channel.guild.id, interaction.channel.id)
        channel_state = ChannelState(channel_state_id)
        await self.update_channel(
            interaction,
            channel_state,
        )

    async def modify_button_callback(self, interaction: discord.Interaction):
        if self.database.get_owner_id(interaction.channel.id) != interaction.user.id:
            return await error_handling.handle_channel_owner_error(interaction)

        modal = ModifyChannelModal(self.bot, self.database, interaction.channel)
        await interaction.response.send_modal(modal)

    async def kick_button_callback(self, interaction: discord.Interaction):
        if self.database.get_owner_id(interaction.channel.id) != interaction.user.id:
            return await error_handling.handle_channel_owner_error(interaction)

        await KickControlView(self.bot, self.database, interaction.channel).send_initial_message(interaction)

    async def clear_button_callback(self, interaction: discord.Interaction):
        if self.database.get_owner_id(interaction.channel.id) != interaction.user.id:
            return await error_handling.handle_channel_owner_error(interaction)
        await interaction.response.defer(ephemeral=True)

        # Fetch messages from the channel
        messages_to_delete = []
        async for message in interaction.channel.history(limit=None):
            # Exclude the message with the last_followup_message_id
            if message.id != self.last_followup_message_id and message.id != interaction.message.id:
                messages_to_delete.append(message)

        # Bulk delete the filtered messages
        if messages_to_delete:
            await interaction.channel.delete_messages(messages_to_delete)

        await interaction.followup.send(f"Deleted {len(messages_to_delete)} messages.", ephemeral=True)

    async def delete_button_callback(self, interaction: discord.Interaction):
        if self.database.get_owner_id(interaction.channel.id) != interaction.user.id:
            return await error_handling.handle_channel_owner_error(interaction)

        # Ask for confirmation
        await interaction.response.send_message("Are you sure you want to delete this channel? Reply with 'yes' within 60 seconds to confirm.", ephemeral=True)

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
                await interaction.followup.send("Channel deletion timed out. No action was taken.", ephemeral=True)
            except e:
                pass

    async def give_button_callback(self, interaction: discord.Interaction):
        if self.database.get_owner_id(interaction.channel.id) != interaction.user.id:
            return await error_handling.handle_channel_owner_error(interaction)

        await interaction.response.send_message(f"Sorry, this button doesnt currently work.", ephemeral=True)

    async def claim_button_callback(self, interaction: discord.Interaction):
        owner_id = self.database.get_owner_id(interaction.channel.id)
        if owner_id is not None:
            owner = await interaction.guild.fetch_member(owner_id)
            await interaction.response.send_message(f"This channel is already owned by {owner.mention}", ephemeral=True)
        elif interaction.user not in interaction.channel.members:
            await interaction.response.send_message("You must be connected to this channel to claim it", ephemeral=True)
        elif owner_id is None and interaction.user in interaction.channel.members:
            self.database.set_owner_id(interaction.channel.id, interaction.user.id)
            await interaction.response.send_message("You are now the owner of this channel", ephemeral=True)

    async def update_channel(self, interaction, new_state: ChannelState):
        if self.database.get_owner_id(interaction.channel.id) != interaction.user.id:
            return await error_handling.handle_channel_owner_error(interaction)

        await interaction.response.defer()

        owner_id = self.database.get_owner_id(interaction.channel.id)
        if not interaction.user.id == owner_id:
            return await error_handling.handle_channel_owner_error(interaction)

        if new_state == ChannelState.PUBLIC:
            permissions = {'connect': True, 'view_channel': True}
        elif new_state == ChannelState.LOCKED:
            permissions = {'connect': False, 'view_channel': True}
        elif new_state == ChannelState.HIDDEN:
            permissions = {'view_channel': False}
        else:
            await error_handling.handle_global_error("Unexpected channel state")
            return

        # set permissions and channel_state in database
        connected_users = [member for member in interaction.channel.members if not member.bot]
        for user in connected_users:
            await interaction.channel.set_permissions(user, connect=True, view_channel=True)
        await interaction.channel.set_permissions(interaction.guild.default_role, **permissions)
        self.database.update_channel_state(interaction.channel.guild.id, interaction.channel.id, new_state.value)

        # update the control menu with wrong followup message. this gets a response to the user quicker but may break when spammed
        view, embed = await create_control_menu(self.bot, self.database, interaction.channel, self.last_followup_message_id)
        await interaction.message.edit(embed=embed, view=view)

        # Create or update followup message
        text, view, embed = await create_followup_menu(self.bot, self.database, interaction.channel)

        # Try to fetch the last follow-up message, if exists
        followup_message = None
        if self.last_followup_message_id:
            try:
                followup_message = await interaction.channel.fetch_message(self.last_followup_message_id)
            except discord.NotFound:
                followup_message = None
        # Edit the followup message if it exists, otherwise send a new follow-up
        if followup_message:
            await followup_message.edit(content=text, view=view, embed=embed)
        else:
            followup_message = await interaction.followup.send(content=text, view=view, embed=embed)

        # update the control menu with correct followup message
        view, embed = await create_control_menu(self.bot, self.database, interaction.channel, followup_message.id)
        await interaction.message.edit(embed=embed, view=view)

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


class ModifyChannelModal(discord.ui.Modal, title="Edit Your Channel"):
    def __init__(self, bot: commands.Bot, database: databasecontrol.Database, channel):
        super().__init__()
        self.bot = bot
        self.database = database
        self.channel = channel

        # Define the text inputs
        channel_name = discord.ui.TextInput(
            label=f"Channel Name",
            placeholder=f"{channel.name}",
            required=False,
            max_length=25
        )
        user_limit = discord.ui.TextInput(
            label="User Limit (Unlimited = 0)",
            placeholder=f"{channel.user_limit}",
            required=False,
            max_length=2
        )

        self.add_item(channel_name)
        self.add_item(user_limit)

    async def on_submit(self, interaction: discord.Interaction):
        # Create a new voice channel and add it to the database
        channel_name = interaction.data["components"][0]["components"][0]["value"]
        if channel_name == "":
            channel_name = self.channel.name
        user_limit = interaction.data["components"][1]["components"][0]["value"]
        if user_limit == "":
            user_limit = self.channel.user_limit
        else:
            user_limit = int(user_limit)

        await self.channel.edit(name=channel_name, user_limit=user_limit)
        await interaction.response.send_message("Your channel has been updated", ephemeral=True)


class ControlTempChannelsCog(commands.Cog):
    def __init__(self, bot: commands.Bot, database):
        self.bot = bot
        self.database = database
        self.last_followup_message_id = None

    @discord.app_commands.command(name="control", description="Control your temp channel")
    @discord.app_commands.checks.has_permissions(manage_channels=True)
    async def control(self, interaction: discord.Interaction):
        try:
            # Create an embed with options
            view, embed = await create_control_menu(self.bot, self.database, temp_channel)
            await interaction.channel.send(embed=embed, view=view)
        except Exception as error:
            await error_handling.handle_command_error(interaction, error)

    @control.error
    async def control_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await error_handling.handle_user_permission_error("manage_channels", interaction)
        else:
            await error_handling.handle_command_error(interaction, error)


async def setup(bot: commands.Bot, database):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(ControlTempChannelsCog(bot, database))
