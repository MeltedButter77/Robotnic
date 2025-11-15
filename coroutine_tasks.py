import discord
import asyncio
from cogs import voice_logic


# All functions within this file will:
# 1. Be called using discord.Bot.loop.create_task() within the main file.
# 2. Have 2 inputs; bot and logger.


async def create_tasks(bot):
    tasks = []
    current_module = __import__(__name__)

    functions = [update_temp_channel_names, update_presence, clear_empty_temp_channels]
    for func in functions:
        tasks.append(bot.loop.create_task(func(bot)))

    bot.logger.debug(f"Created {len(tasks)} coroutine tasks")
    return tasks


async def update_temp_channel_names(bot):
    await bot.wait_until_ready()  # Ensure the bot is fully connected
    while not bot.is_closed():  # Run on a schedule
        bot.logger.debug("Updating temp channel names...")
        try:
            # Update numbers of temp channels
            bot.db.fix_temp_channel_numbers()

            # Calculate what each temp channel's name should be and schedule and update if they don't match
            temp_channel_ids = bot.db.get_temp_channel_ids()
            for temp_channel_id in temp_channel_ids:
                temp_channel = bot.get_channel(temp_channel_id)
                db_temp_channel_info = bot.db.get_temp_channel_info(temp_channel.id)
                if temp_channel and db_temp_channel_info.creator_id:
                    new_channel_name = voice_logic.create_temp_channel_name(bot, temp_channel, db_temp_channel_info=db_temp_channel_info)

                    # If the current name is different to the correct name, rename it.
                    if temp_channel.name != new_channel_name:
                        # Use bot.renamer to reduce rate-limit problems
                        bot.logger.debug(f"Renaming {temp_channel.name} to {new_channel_name}")
                        # await temp_channel.edit(name=new_channel_name)
                        await bot.renamer.schedule_name_update(temp_channel, new_channel_name)

        except Exception as e:
            bot.logger.error(f"Error in {__name__} task: {e}")

        await asyncio.sleep(20)  # 1 minute (60 seconds)


async def update_presence(bot):
    await bot.wait_until_ready()  # Ensure the bot is fully connected
    while not bot.is_closed():  # Run on a schedule
        try:
            server_count = len(bot.guilds)
            member_count = 0
            for guild in bot.guilds:
                member_count += guild.member_count
            status_text = f"Online in {server_count} servers. Serving {member_count} users."
            await bot.change_presence(activity=discord.Game(status_text))
            bot.logger.debug(f"Updated presence to \'{status_text}\'")

        except Exception as e:
            bot.logger.error(f"Error in {__name__} task: {e}")

        await asyncio.sleep(3600)  # 1 hour (3600 seconds)


async def clear_empty_temp_channels(bot):
    await bot.wait_until_ready()  # Ensure the bot is fully connected
    while not bot.is_closed():  # Run on a schedule
        try:
            bot.logger.debug("Clearing empty temp channels...")

            temp_channel_ids = bot.db.get_temp_channel_ids()
            creator_channel_ids = bot.db.get_creator_channel_ids()

            # Cleanup deleted creator channels
            for channel_id in creator_channel_ids:
                channel = bot.get_channel(channel_id)
                if channel is None:
                    bot.logger.debug(f"Removing unfound/deleted creator channel from database")
                    bot.db.remove_creator_channel(channel_id)

            # Clean up empty temp channels
            for channel_id in temp_channel_ids:
                channel = bot.get_channel(channel_id)
                if channel is None:
                    bot.logger.debug(f"Removing unfound/deleted temp channel from database")
                    bot.db.remove_temp_channel(channel_id)
                    continue

                # Having member intent should mean this is not needed
                if not channel.guild.chunked:  # Only chunk if not already done
                    bot.logger.debug(f"Fetching all members for guild {channel.guild.name} to populate cache")
                    await channel.guild.chunk()

                if len(channel.members) == 0:
                    bot.logger.debug(f"Deleting empty temp channel \'{channel.name}\'")
                    bot.db.remove_temp_channel(channel.id)
                    await channel.delete()

        except Exception as e:
            bot.logger.error(f"Error in {__name__} task: {e}")

        await asyncio.sleep(120)  # 2 minutes (120 seconds)
