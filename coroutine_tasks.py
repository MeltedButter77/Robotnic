import pathlib
import json
import discord
import asyncio
import cogs.voice_logic


async def create_tasks(bot):
    tasks = []
    current_module = __import__(__name__)

    # These are the functions in this file that will run periodically in bot.loop
    functions = [update_temp_channel_names, update_presence, clear_empty_temp_channels]
    for func in functions:
        tasks.append(bot.loop.create_task(func(bot)))

    bot.logger.debug(f"Created {len(tasks)} coroutine tasks")
    return tasks


# Technically shouldn't be required as cogs.voice_logic.update_channel_name_and_control_msg is run every time a user leaves a vc
# This is here in case of desync. Hopefully can be removed once the bot is tested properly
async def update_temp_channel_names(bot):
    await bot.wait_until_ready()  # Ensure the bot is fully connected
    while not bot.is_closed():  # Run on a schedule
        try:
            bot.logger.debug(f"Updating all temp channel names on schedule")
            temp_channel_ids = bot.db.get_temp_channel_ids()
            await cogs.voice_logic.update_channel_name_and_control_msg(bot, temp_channel_ids)
        except Exception as e:
            bot.logger.error(f"Error in {__name__} task: {e}")
        await asyncio.sleep(90)  # 1.5 minutes (90 seconds)


async def update_presence(bot):
    await bot.wait_until_ready()  # Ensure the bot is fully connected
    while not bot.is_closed():  # Run on a schedule
        try:
            status_text = bot.settings["status"].get("text", "")

            # Create variables if needed
            server_count = len(bot.guilds)  # Always needed as used in top.gg post
            if "{member_count}" in status_text:
                member_count = 0
                for guild in bot.guilds:
                    member_count += guild.member_count

            # Formate from settings
            status = status_text.format(**locals())
            await bot.change_presence(activity=discord.Game(status))
            bot.logger.debug(f"Updated presence to \'{status}\'")

            # Post guild count to TopGG
            if bot.topgg_client:
                await bot.topgg_client.post_guild_count()
                bot.logger.debug(f"Posted Guild Count to TOPGG; {server_count}")

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
            # creator_channel_ids = bot.db.get_creator_channel_ids()

            # Cleanup deleted creator channels
            # for channel_id in creator_channel_ids:
            #     channel = bot.get_channel(channel_id)
            #     if channel is None:
            #         bot.logger.debug(f"Removing unfound/deleted creator channel from database")
            #         bot.db.remove_creator_channel(channel_id)

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
                    await channel.delete()
                    bot.db.remove_temp_channel(channel.id)

        except Exception as e:
            bot.logger.error(f"Error in {__name__} task: {e}")

        await asyncio.sleep(300)  # 5 minutes (300 seconds)
