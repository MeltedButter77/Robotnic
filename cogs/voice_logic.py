import asyncio
import time
import discord
from discord.ext import commands
from cogs.voice_control import ButtonsView
import cogs.voice_control


class VoiceLogicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        # Updates temp channel name if child_name_template has activities and a connected user changes activities
        if after.voice and after.voice.channel:
            temp_channel = after.voice.channel

            db_temp_channel_info = self.bot.db.get_temp_channel_info(temp_channel.id)
            if not db_temp_channel_info:
                return
            db_creator_channel_info = self.bot.db.get_creator_channel_info(db_temp_channel_info.creator_id)
            if db_temp_channel_info is not None and "{activity}" in str(db_creator_channel_info.child_name):
                new_channel_name = create_temp_channel_name(self.bot, temp_channel)
                # If the current name is different to the correct name, rename it.
                if temp_channel.name != new_channel_name:
                    self.bot.logger.debug(f"Renaming {temp_channel.name} to {new_channel_name} due to activity change")
                    await self.bot.renamer.schedule_name_update(temp_channel, new_channel_name)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if after.channel:  # If a user joined a channel
            creator_channel_ids = self.bot.db.get_creator_channel_ids()
            if after.channel.id in creator_channel_ids:  # Filter to creator channels
                await create_on_join(member, before, after, self.bot)

        if before.channel:  # If a user left a channel
            temp_channel_ids = self.bot.db.get_temp_channel_ids()
            if before.channel.id in temp_channel_ids:  # Filter to temp channels
                await delete_on_leave(member, before, after, self.bot)


def setup(bot):
    bot.add_cog(VoiceLogicCog(bot))


# Updates channel name to match its creator's template.
# Updates Control message's info embed to reflect true data
async def update_channel_name_and_control_msg(bot, temp_channel_ids):
    bot.db.fix_temp_channel_numbers()

    async def update(temp_channel_id):
        temp_channel = bot.get_channel(temp_channel_id)
        db_temp_channel_info = bot.db.get_temp_channel_info(temp_channel_id)
        if db_temp_channel_info.is_renamed:
            return
        if not temp_channel or not db_temp_channel_info.creator_id:
            return

        # Rename channel if not renamed and new name is different
        new_channel_name = None
        if not db_temp_channel_info.is_renamed:
            new_channel_name = create_temp_channel_name(
                bot, temp_channel, db_temp_channel_info=db_temp_channel_info
            )
            if temp_channel.name != new_channel_name:
                bot.logger.debug(f"Renaming {temp_channel.name} to {new_channel_name}")
                await bot.renamer.schedule_name_update(temp_channel, new_channel_name)

        # Update control message
        async for control_message in temp_channel.history(limit=3, oldest_first=True):
            if control_message.author.id == bot.user.id:
                new_info_embed = cogs.voice_control.ChannelInfoEmbed(bot, temp_channel, title=new_channel_name)
                if control_message.embeds[0].title != new_info_embed.title:
                    bot.logger.debug(f"Updating Control Message")
                    embeds = [new_info_embed, control_message.embeds[1]]
                    await control_message.edit(embeds=embeds)
                break

    # Run all updates concurrently
    tasks = (update(channel_id) for channel_id in temp_channel_ids)
    await asyncio.gather(*tasks)


# - This class fixes rate-limit renaming problems
# - Previously if a channel were to be updated 3 times in a row (user playing word -> launcher -> game)
# - (depending on timing) Channel could be rate-limited and the channel is renamed word then rate limited,
# renamed launcher then limited and finally game after far too long.
# - This class should prevent old rate-limited names from being applied if a more recent up-to-date name is preferable
# - To use this, use: await bot.renamer.schedule_name_update(temp_channel, new_name) instead of: await temp_channel.edit(name=new_name)
class TempChannelRenamer:
    def __init__(self, bot):
        self.bot = bot
        self.pending = {}  # channel_id -> RenameState
        self.last_edit_time = {}  # channel_id → timestamp
        self.min_interval = 30.0  # seconds between edits

    class RenameState:
        def __init__(self, new_name):
            self.desired_name = new_name
            self.version = time.time()
            self.task = None

    async def schedule_name_update(self, temp_channel, new_name):
        cid = temp_channel.id

        # If channel has no pending state
        if cid not in self.pending:
            self.pending[cid] = self.RenameState(new_name)
        else:
            # Update existing name and version stamp
            state = self.pending[cid]
            state.desired_name = new_name
            state.version = time.time()

        # If a task is already running, don’t start another
        if self.pending[cid].task is not None:
            return

        # Create an async task to process update
        self.pending[cid].task = asyncio.create_task(
            self._perform_update(temp_channel, cid)
        )

    async def _perform_update(self, temp_channel, cid):
        now = time.time()
        last = self.last_edit_time.get(cid, 0)

        # Enforce cooldown of min_interval. Prevents discord hard rate-limits of 10-15 minutes
        if now - last < self.min_interval:
            self.bot.logger.debug("Waiting to rename channel to enforce minimum interval.")
            wait_time = self.min_interval - (now - last)
            await asyncio.sleep(wait_time)

        state = self.pending[cid]
        start_version = state.version

        # Debounce window, prevents rapid spam
        await asyncio.sleep(1.0)

        # If a newer update request occurred, ignore this one
        if state.version != start_version:
            # Allow a future update to be scheduled
            self.pending[cid].task = None
            return

        # Perform the actual rename
        try:
            await temp_channel.edit(name=state.desired_name)
            self.last_edit_time[cid] = time.time()
        except discord.HTTPException as error:
            if error.status == 429:
                self.bot.logger.debug("Rate limited by discord.")
                return
            else:
                raise

        # Marks task as finished
        self.pending[cid].task = None


def create_temp_channel_name(bot, temp_channel, db_temp_channel_info=None, db_creator_channel_info=None):
    if not temp_channel:
        return None

    # Allows db info to be passed in if it was already retrieved for something else. Choice reduces db reads
    if not db_temp_channel_info:
        db_temp_channel_info = bot.db.get_temp_channel_info(temp_channel.id)
    if not db_creator_channel_info:
        db_creator_channel_info = bot.db.get_creator_channel_info(db_temp_channel_info.creator_id)

    # Uses guild.get_member rather than bot.get_member to access nicknames
    owner = temp_channel.guild.get_member(db_temp_channel_info.owner_id) if db_temp_channel_info.owner_id else None

    new_channel_name = db_creator_channel_info.child_name
    if "{user}" in str(new_channel_name):
        if owner:
            member_name = owner.nick if owner.nick else owner.display_name
        else:
            member_name = "None"
        new_channel_name = new_channel_name.replace("{user}", member_name)

    if "{activity}" in str(new_channel_name):
        activities = []
        for member in temp_channel.members:
            for activity in member.activities:
                if activity.type == discord.ActivityType.playing:
                    if activity.name.lower() not in (name.lower() for name in activities):
                        activities.append(activity.name)

        if len(activities) <= 0:
            activities.append("General")
        activities.sort(key=len)
        activity_text = ", ".join(activities)

        new_channel_name = new_channel_name.replace("{activity}", activity_text)

    if "{count}" in str(new_channel_name):
        count = db_temp_channel_info.number
        new_channel_name = new_channel_name.replace("{count}", str(count))

    # Max char is 100, using 98 just in case
    if len(str(new_channel_name)) > 95:
        new_channel_name = new_channel_name[:95] + "..."

    return new_channel_name


async def create_on_join(member, before, after, bot):
    bot.logger.debug(f"{member} joined creator channel {after.channel}")

    # Logic flow:
    # 1. Retrieve child settings from db
    # 2. Get category & overwrites, both depend on settings
    # 3. Create channel & move user
    # 4. Create name
    # 5. Edit channel w correct name & overwrites and disable permission sync

    # SETTINGS from db
    # Category:
    # 0 -> Creator channel category
    # id -> Specific category
    # Note: no way to make channel have no category if the creator has a category
    # Overwrites:
    # 0 -> no overwrites
    # 1 -> overwrites from creator
    # 2 -> overwrites from category
    # User Limit:
    # 0 -> unlimited
    # int -> that amount
    # Name Template:
    # {user} - replaced by users nickname or display name
    # {activity} - not implemented
    # {count} - not implemented

    creator_channel = after.channel

    db_creator_channel_info = bot.db.get_creator_channel_info(creator_channel.id)
    if db_creator_channel_info.child_category_id != 0:
        category = bot.get_channel(db_creator_channel_info.child_category_id)
    else:
        category = creator_channel.category

    # 0 -> no overwrites
    # 1 -> overwrites from creator
    # 2 -> overwrites from category
    if db_creator_channel_info.child_overwrites == 1:
        overwrites = creator_channel.overwrites
    elif db_creator_channel_info.child_overwrites == 2:
        overwrites = category.overwrites
    else:
        overwrites = {}

    overwrites[bot.user] = discord.PermissionOverwrite(
        view_channel=True,
        manage_channels=True,
        send_messages=True,
        manage_messages=True,
        read_message_history=True,
        connect=True,
        move_members=True,
    )
    overwrites[member] = discord.PermissionOverwrite(
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        connect=True,
    )

    try:
        new_temp_channel = await creator_channel.guild.create_voice_channel(
            name="⌛",
            category=category,
            overwrites=overwrites,
            position=creator_channel.position,
        )
    except discord.Forbidden as e:
        bot.logger.debug(f"Permission error creating temp channel, handled by sending a message notifying of lack of perms. {e}")
        embed = discord.Embed()
        embed.add_field(name="Required", value="`view_channel`, `manage_channels`, `send_messages`, `manage_messages`, `read_message_history`, `connect`, `move_members`")
        await creator_channel.send(f"Sorry {member.mention}, I require the following permissions. Make sure they are not overwritten by the category (In this case `{category.name}`).", embed=embed, delete_after=300)
        return

    counts = bot.db.get_temp_channel_counts(creator_channel.id)
    if len(counts) < 1:
        count = 1
    else:
        count = max(counts) + 1

    bot.db.add_temp_channel(new_temp_channel.guild.id, new_temp_channel.id, creator_channel.id, member.id, 0, count, False)

    try:
        await member.move_to(new_temp_channel)
        bot.logger.debug(f"Moved {member} to {new_temp_channel}")
    except Exception as e:
        bot.logger.debug(f"Error creating voice channel, most likely a quick join and leave. Handled. {e}")
        bot.db.remove_temp_channel(new_temp_channel.id)
        await new_temp_channel.delete()
        return

    channel_name = create_temp_channel_name(bot, new_temp_channel, db_creator_channel_info=db_creator_channel_info)

    # Disable sync and reapply overwrites. this is because creating a channel in a
    # category with no overwrites will auto get overwrites of the category even if
    # {} is passed in overwrites
    try:
        # Use bot.renamer to avoid rate-limit problems
        await new_temp_channel.edit(
            name=channel_name,
            user_limit=db_creator_channel_info.user_limit,
            sync_permissions=False,
            overwrites=overwrites
        )

        # Send control message in channel chat
        await asyncio.sleep(2)  # Allows time for channel to be edited to correct name
        view = ButtonsView(bot, new_temp_channel)
        await view.send_initial_message()
    except Exception as e:
        bot.logger.debug(f"Error finalizing creation of voice channel, handled. {e}")
        bot.db.remove_temp_channel(new_temp_channel.id)

    if bot.notification_channel:
        await bot.notification_channel.send(f"Temp Channel (`{new_temp_channel.name}`) was made in server (`{member.guild.name}`) by user (`{member}`)")


async def delete_on_leave(member, before, after, bot):
    if len(before.channel.members) < 1:
        bot.logger.debug(f"Left temp channel is empty. Deleting...")

        try:
            await before.channel.delete()
            bot.db.remove_temp_channel(before.channel.id)
        except discord.NotFound as e:
            bot.db.remove_temp_channel(before.channel.id)
            bot.logger.debug(f"Channel not found removing entry in db, handled. {e}")
        except discord.Forbidden as e:
            bot.logger.debug(f"Permission error removing temp channel, handled by sending a message notifying of lack of perms. {e}")
            await before.channel.send(f"Sorry {member.mention}, I do not have permission to delete this channel.", delete_after=300)
            return
        except Exception as e:
            bot.logger.error(f"Unknown error removing temp channel. {e}")

        if bot.notification_channel:
            await bot.notification_channel.send(f"Temp Channel was removed in server (`{member.guild.name}`) by user (`{member}`)")
