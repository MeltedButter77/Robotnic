import inspect

import discord
import asyncio

# All functions within this file will:
# 1. Be called using discord.Bot.loop.create_task() within the main file.
# 2. Have 2 inputs; bot and logger.


async def create_tasks(bot, logger):
    tasks = []
    current_module = __import__(__name__)

    for name, func in inspect.getmembers(current_module, inspect.iscoroutinefunction):
        if name == "create_tasks":
            continue
        logger.debug(f"Creating coroutine task {name}")
        tasks.append(bot.loop.create_task(func(bot, logger)))

    logger.info(f"Created {len(tasks)} coroutine tasks")
    return tasks


async def update_presence(bot, logger):
    await bot.wait_until_ready()  # Ensure the bot is fully connected
    while not bot.is_closed():  # Run on a schedule
        try:
            server_count = len(bot.guilds)
            member_count = 0
            for guild in bot.guilds:
                member_count += guild.member_count
            status_text = f"Online in {server_count} servers. Serving {member_count} users."
            await bot.change_presence(activity=discord.Game(status_text))
            logger.debug(f"Updated presence to \'{status_text}\'")

        except Exception as e:
            logger.error(f"Error in {__name__} task: {e}")

        await asyncio.sleep(3600)  # 1 hour (3600 seconds)


async def clear_empty_temp_channels(bot, logger):
    await bot.wait_until_ready()  # Ensure the bot is fully connected
    while not bot.is_closed():  # Run on a schedule
        try:
            logger.debug("Clearing empty temp channels...")

            count, db_count = 0, 0
            temp_channel_ids = bot.db.get_temp_channel_ids()

            # Example: clean up empty temp channels
            for channel_id in temp_channel_ids:
                channel = bot.get_channel(channel_id)
                if channel is None:
                    logger.debug(f"Removing unfound/deleted temp channel from database")
                    bot.db.remove_temp_channel(channel_id)
                    continue

                if bot.db.is_temp_channel(channel.id) and len(channel.members) == 0:
                    logger.debug(f"Deleting empty temp channel \'{channel.name}\'")
                    bot.db.remove_temp_channel(channel.id)
                    await channel.delete()

        except Exception as e:
            logger.error(f"Error in {__name__} task: {e}")

        await asyncio.sleep(120)  # 2 minutes (120 seconds)
