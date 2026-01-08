import asyncio
import time
import discord


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
