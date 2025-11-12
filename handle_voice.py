import asyncio


async def create_on_join(member, before, after, bot, logger):
    logger.debug(f"{member} joined creator channel {after.channel}")

    new_temp_channel = await after.channel.guild.create_voice_channel("name")
    bot.db.add_temp_channel(new_temp_channel.guild.id, new_temp_channel.id, after.channel.id, member.id, 0, 1, False)

    try:
        await member.move_to(new_temp_channel)
        logger.debug(f"Moved {member} to {new_temp_channel}")
    except Exception as e:
        logger.debug(f"Error creating voice channel, handled. {e}")
        bot.db.remove_temp_channel(new_temp_channel.id)
        await new_temp_channel.delete()


async def delete_on_leave(member, before, after, bot, logger):
    logger.debug(f"{member} left temp channel {before.channel}")

    if len(before.channel.members) < 1:
        logger.debug(f"Left temp channel is empty. Deleting...")

        bot.db.remove_temp_channel(before.channel.id)
        await before.channel.delete()


async def update(member, before, after, bot, logger):
    if after.channel:  # If a user joined a channel
        creator_channel_ids = bot.db.get_creator_channel_ids()
        if after.channel.id in creator_channel_ids:  # Filter to creator channels
            await create_on_join(member, before, after, bot, logger)

    if before.channel:  # If a user left a channel
        temp_channel_ids = bot.db.get_temp_channel_ids()
        if before.channel.id in temp_channel_ids:  # Filter to temp channels
            await delete_on_leave(member, before, after, bot, logger)


async def clear_empty_temp_channels(bot, logger):
    await bot.wait_until_ready()  # Ensure the bot is fully connected
    while not bot.is_closed():  # Run on a schedule
        try:
            logger.debug("Clearing empty temp channels...")

            temp_channel_ids = bot.db.get_temp_channel_ids()

            # Example: clean up empty temp channels
            for channel_id in temp_channel_ids:
                channel = bot.get_channel(channel_id)
                if channel is None:
                    logger.debug(f"Removing unfound/deleted temp channel from database")
                    bot.db.remove_temp_channel(channel_id)
                    continue

                if bot.db.is_temp_channel(channel.id) and len(channel.members) == 0:
                    logger.debug(f"Deleting empty temp channel {channel.name}")
                    bot.db.remove_temp_channel(channel.id)
                    await channel.delete()

        except Exception as e:
            logger.error(f"Error in periodic task: {e}")

        await asyncio.sleep(120)  # 2 minutes (120 seconds)
