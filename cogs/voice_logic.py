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
    async def on_voice_state_update(self, member, before, after):
        # Filter out normal updates when not switching channels
        if before is not None and after is not None:
            if before.channel == after.channel:
                return

        if after.channel:  # If a user joined a channel
            creator_channel_ids = self.bot.db.get_creator_channel_ids()
            if after.channel.id in creator_channel_ids:  # Filter to creator channels
                await create_on_join(member, before, after, self.bot)

        if before.channel:  # If a user left a channel
            temp_channel_ids = self.bot.db.get_temp_channel_ids()
            if before.channel.id in temp_channel_ids:  # Filter to temp channels
                await delete_on_leave(member, before, after, self.bot)

                # Update channel names of all temp channels
                # Technically channel names only need to be updated on activity change and deleting a channel (this), no coroutine needed.
                # Future optimisation, This should also only update channels in this server
                temp_channel_ids = self.bot.db.get_temp_channel_ids()
                await update_channel_name_and_control_msg(self.bot, temp_channel_ids)

    # If user's activity changes while in a temp vc, update its name
    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        if not hasattr(after, "channel"):
            return
        temp_channel = after.channel

        self.bot.logger.debug(f"Updating {temp_channel.name} due to activity change")
        await update_channel_name_and_control_msg(self.bot, [temp_channel.id])


def setup(bot):
    bot.add_cog(VoiceLogicCog(bot))


# Updates channel name to match its creator's template.
# Updates Control message's info embed to reflect true data
async def update_channel_name_and_control_msg(bot, temp_channel_ids):
    bot.logger.debug(f"Updating {len(temp_channel_ids)} temp channel names & control msgs...")
    start = time.perf_counter()

    # Fixes any badly ordered channel count in the db
    # name update will reflect the db, so we fix it first
    bot.db.fix_temp_channel_numbers()

    async def update(temp_channel_id):
        temp_channel = bot.get_channel(temp_channel_id)
        db_temp_channel_info = bot.db.get_temp_channel_info(temp_channel_id)
        if db_temp_channel_info.is_renamed:
            return
        if not temp_channel or not db_temp_channel_info.creator_id:  # Filter so only channels in the temp_channels db continue
            return

        new_channel_name = None
        if not db_temp_channel_info.is_renamed:
            new_channel_name = create_temp_channel_name(
                bot, temp_channel, db_temp_channel_info=db_temp_channel_info
            )

            # Rename channel if not renamed and new name is different
            if temp_channel.name != new_channel_name:
                if len(temp_channel.members) > 0:  # If empty it is going to be deleted, ignore
                    bot.logger.debug(f"Renaming {temp_channel.name} to {new_channel_name}")
                    await bot.renamer.schedule(temp_channel, new_channel_name)
                    # await temp_channel.edit(name=new_channel_name)

        # Update control message
        await cogs.voice_control.update_info_embed(bot, temp_channel, title=new_channel_name)

    # Run all updates concurrently
    tasks = (update(channel_id) for channel_id in temp_channel_ids)
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        bot.logger.debug(f"Unhandled error in func update_channel_name_and_control_msg {e}")

    end = time.perf_counter()
    duration = end - start
    bot.logger.debug(f"Temp channel name update completed in {duration:.4f} seconds")


# - This class fixes rate-limit renaming problems
# - Previously if a channel were to be updated 3 times in a row (user playing word -> launcher -> game)
# - (depending on timing) Channel could be rate-limited and the channel is renamed word then rate limited,
# renamed launcher then limited and finally game after far too long.
# - This class should prevent old rate-limited names from being applied if a more recent up-to-date name is preferable
# - To use this, use: await bot.renamer.schedule(temp_channel, new_name) instead of: await temp_channel.edit(name=new_name)
class TempChannelRenamer:
    def __init__(self, bot):
        self.bot = bot

        # Each channel ID stores its own new_name (next name it will have once rate-limit gone)
        self.name_queues = {}  # channel_id - asyncio.Queue()

        # Each channel ID stores a worker task that processes renames
        self.rename_workers = {}  # channel_id - asyncio.Task()

        # Tracks when each channel was last renamed
        self.last_rename_time = {}  # channel_id - timestamp

        # Minimum safe time between renames (10 minutes)
        self.minimum_interval = 600.0

    async def schedule(self, channel: discord.abc.GuildChannel, new_name: str):
        """
        Request that a channel be renamed.
        Only the most recent name requested is kept.
        """

        # Create a queue for this channel if needed
        self.name_queues[channel.id] = new_name
        self.bot.logger.debug(f"[RENAMER] Queued rename request for channel {channel.name} ({channel.id}): '{new_name}'.")

        # Start a worker for this channel if none exists
        if (channel.id not in self.rename_workers or self.rename_workers[channel.id].done()):
            self.rename_workers[channel.id] = asyncio.create_task(self._worker(channel))
            self.bot.logger.debug(f"[RENAMER] Started worker task for channel {channel.name} ({channel.id})")

    async def _worker(self, channel):
        """
        Worker task that processes rename requests for a single channel.
        It exits when no more rename requests exist.
        """

        new_name = self.name_queues[channel.id]

        while True:
            self.bot.logger.debug(
                f"[RENAMER] Worker for channel {channel.name} ({channel.id}) received rename request '{new_name}'.")

            # Small delay to collect multiple rapid rename requests
            await asyncio.sleep(1.0)

            # Enforce the minimum time between renames
            last_time = self.last_rename_time.get(channel.id, 0)
            time_since_last = time.time() - last_time
            time_remaining = self.minimum_interval - time_since_last
            if time_remaining > 0:
                self.bot.logger.debug(
                    f"[RENAMER] Channel {channel.name} ({channel.id}) must wait {time_remaining:.2f} seconds before renaming again.")
                await asyncio.sleep(time_remaining)

            # Get new name which may have changed while waiting
            new_name = self.name_queues[channel.id]

            self.bot.logger.debug(f"[RENAMER] Renaming channel {channel.name} ({channel.id}) to '{new_name}'.")

        # Try to perform the rename
            try:
                if channel.name != new_name:
                    await channel.edit(name=new_name)
                    self.bot.logger.debug(f"[RENAMER] Successfully renamed channel {channel.name} ({channel.id}) to '{new_name}'.")
                    self.last_rename_time[channel.id] = time.time()
                else:
                    self.bot.logger.debug(f"[RENAMER] Channel {channel.name} ({channel.id}) is already named '{new_name}'.")
                new_name = None

            except discord.HTTPException as error:
                if error.status == 429:
                    # The library almost never throws this.
                    retry_seconds = getattr(error, "retry_after", 10)
                    self.bot.logger.warning(
                        f"[RENAMER] Channel {channel.name} ({channel.id}) hit a rate limit. Retrying in {retry_seconds + 1} seconds.")
                    await asyncio.sleep(retry_seconds + 1)
                    continue
                else:
                    raise

            # If there are no pending rename requests, exit the worker
            if new_name is None:
                self.bot.logger.debug(f"[RENAMER] Worker has renamed {channel.name} ({channel.id}). Exiting.")
                break

        # Cleanup after the worker finishes
        self.name_queues.pop(channel.id, None)
        self.rename_workers.pop(channel.id, None)


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
            member_name = "Public"
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
    # 6. Send logs and notifications messages

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
        bot.logger.debug(
            f"Permission error creating temp channel, handled by sending a message notifying of lack of perms. {e}")
        embed = discord.Embed()
        embed.add_field(name="Required",
                        value="`view_channel`, `manage_channels`, `send_messages`, `manage_messages`, `read_message_history`, `connect`, `move_members`")
        await creator_channel.send(
            f"Sorry {member.mention}, I require the following permissions. Make sure they are not overwritten by the category (In this case `{category.name}`).",
            embed=embed, delete_after=300)
        return

    counts = bot.db.get_temp_channel_counts(creator_channel.id)
    if len(counts) < 1:
        count = 1
    else:
        count = max(counts) + 1

    bot.db.add_temp_channel(new_temp_channel.guild.id, new_temp_channel.id, creator_channel.id, member.id, 0, count,
                            False)

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
        # Could use bot.renamer to avoid rate-limit problems
        await new_temp_channel.edit(
            name=channel_name,
            user_limit=db_creator_channel_info.user_limit,
            sync_permissions=False,
            overwrites=overwrites
        )

        # Send control message in channel chat
        view = ButtonsView(bot, new_temp_channel)
        await view.send_initial_message(channel_name=channel_name)
    except Exception as e:
        bot.logger.debug(f"Error finalizing creation of voice channel, handled. {e}")
        bot.db.remove_temp_channel(new_temp_channel.id)

    # Sends messages in the guild log channel and the bot's notification channel - uses get_guild_logs_channel_id instead of get_guild_settings for read efficiency
    log_channel = bot.get_channel(bot.db.get_guild_logs_channel_id(after.channel.guild.id)["logs_channel_id"])
    if log_channel:
        await log_channel.send(f"New Temp Channel `{new_temp_channel.name} ({new_temp_channel.id})` was made by user `{member} ({member.id}`)")

    # Send bot logging message
    await bot.send_bot_log(type="channel_create", message=f"Temp Channel (`{new_temp_channel.name}`) was made in server (`{member.guild.name}`) by user (`{member}`)")


async def delete_on_leave(member, before, after, bot):
    if len(before.channel.members) < 1:
        bot.logger.debug(f"Left temp channel is empty. Deleting...")

        try:
            await before.channel.delete()
            bot.db.remove_temp_channel(before.channel.id)
            bot.logger.debug(f"Deleted {before.channel.name}")
        except discord.NotFound as e:
            bot.db.remove_temp_channel(before.channel.id)
            bot.logger.debug(f"Channel not found removing entry in db, handled. {e}")
        except discord.Forbidden as e:
            bot.logger.debug(
                f"Permission error removing temp channel, handled by sending a message notifying of lack of perms. {e}")
            await before.channel.send(f"Sorry {member.mention}, I do not have permission to delete this channel.",
                                      delete_after=300)
            return
        except Exception as e:
            bot.logger.error(f"Unknown error removing temp channel. {e}")

        await bot.send_bot_log(type="channel_remove", message=f"Temp Channel was removed in server (`{member.guild.name}`) by user (`{member}`)")

    # Clear owner_id in db if owner leaves
    if len(before.channel.members) >= 1:
        db_temp_channel_info = bot.db.get_temp_channel_info(before.channel.id)
        if db_temp_channel_info:
            if member.id == db_temp_channel_info.owner_id:
                bot.db.set_owner_id(before.channel.id, None)
