import asyncio
import time
import discord


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

    # Max char is 100, using 98 just in case
    if len(str(new_channel_name)) > 95:
        new_channel_name = new_channel_name[:95] + "..."

    return new_channel_name


async def create_on_join(member, before, after, bot, logger):
    logger.debug(f"{member} joined creator channel {after.channel}")

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

    new_temp_channel = await creator_channel.guild.create_voice_channel(
        name="⌛",
        category=category,
        overwrites=overwrites,
    )
    bot.db.add_temp_channel(new_temp_channel.guild.id, new_temp_channel.id, creator_channel.id, member.id, 0, 1, False)

    try:
        await member.move_to(new_temp_channel)
        logger.debug(f"Moved {member} to {new_temp_channel}")
    except Exception as e:
        logger.debug(f"Error creating voice channel, handled. {e}")
        bot.db.remove_temp_channel(new_temp_channel.id)
        await new_temp_channel.delete()

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
    except Exception as e:
        logger.debug(f"Error finalizing creation of voice channel, handled. {e}")
        bot.db.remove_temp_channel(new_temp_channel.id)

    if bot.notification_channel:
        await bot.notification_channel.send(f"Temp Channel was made in `{member.guild.name}` by `{member}`")


async def delete_on_leave(member, before, after, bot, logger):
    if len(before.channel.members) < 1:
        logger.debug(f"Left temp channel is empty. Deleting...")

        bot.db.remove_temp_channel(before.channel.id)
        await before.channel.delete()

        if bot.notification_channel:
            await bot.notification_channel.send(f"Temp Channel was removed in `{member.guild.name}` by `{member}`")


async def update(member, before, after, bot, logger):
    if after.channel:  # If a user joined a channel
        creator_channel_ids = bot.db.get_creator_channel_ids()
        if after.channel.id in creator_channel_ids:  # Filter to creator channels
            await create_on_join(member, before, after, bot, logger)

    if before.channel:  # If a user left a channel
        temp_channel_ids = bot.db.get_temp_channel_ids()
        if before.channel.id in temp_channel_ids:  # Filter to temp channels
            await delete_on_leave(member, before, after, bot, logger)
