import time
import discord
import asyncio
from cogs import voice_logic
from cogs.voice_control import ChannelInfoEmbed


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
    await bot.wait_until_ready()
    while not bot.is_closed():
        start = time.perf_counter()
        bot.logger.debug("Updating temp channel names...")
        try:
            bot.db.fix_temp_channel_numbers()
            temp_channel_ids = bot.db.get_temp_channel_ids()

            async def update_channel(temp_channel_id):
                temp_channel = bot.get_channel(temp_channel_id)
                db_temp_channel_info = bot.db.get_temp_channel_info(temp_channel_id)
                if not temp_channel or not db_temp_channel_info.creator_id:
                    return

                # Rename channel if needed
                new_channel_name = voice_logic.create_temp_channel_name(
                    bot, temp_channel, db_temp_channel_info=db_temp_channel_info
                )
                if temp_channel.name != new_channel_name:
                    bot.logger.debug(f"Renaming {temp_channel.name} to {new_channel_name}")
                    await bot.renamer.schedule_name_update(temp_channel, new_channel_name)

                # Update control message
                async for control_message in temp_channel.history(limit=3, oldest_first=True):
                    if control_message.author.id == bot.user.id:
                        new_info_embed = ChannelInfoEmbed(bot, temp_channel)
                        if control_message.embeds[0].title != new_info_embed.title:
                            bot.logger.debug(f"Updating Control Message")
                            embeds = [new_info_embed, control_message.embeds[1]]
                            await control_message.edit(embeds=embeds)
                        break

            # Run all updates concurrently
            await asyncio.gather(*(update_channel(channel_id) for channel_id in temp_channel_ids))

        except Exception as e:
            bot.logger.error(f"Error in {__name__} task: {e}")

        end = time.perf_counter()
        duration = end - start
        bot.logger.debug(f"Temp channel name update completed in {duration:.4f} seconds")

        await asyncio.sleep(60)


async def update_presence(bot):
    await bot.wait_until_ready()  # Ensure the bot is fully connected
    while not bot.is_closed():  # Run on a schedule
        try:
            server_count = len(bot.guilds)
            member_count = 0
            for guild in bot.guilds:
                member_count += guild.member_count
            status_text = f"Online in {server_count} servers | {member_count} users."
            await bot.change_presence(activity=discord.Game(status_text))
            bot.logger.debug(f"Updated presence to \'{status_text}\'")

        except Exception as e:
            bot.logger.error(f"Error in {__name__} task: {e}")

        await asyncio.sleep(3600)  # 1 hour (3600 seconds)


# Known bug that if this triggers while a user is creating a temp channel and is yet to be moved, this may delete the channel and cause an error
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
