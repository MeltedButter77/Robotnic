import asyncio
import time
from cogs.control_vc.embed_updates import update_info_embed
from cogs.manage_vcs.create_name import create_temp_channel_name


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
                    await bot.TempChannelRenamer.schedule(temp_channel, new_channel_name)

        # Update control message
        await update_info_embed(bot, temp_channel, title=new_channel_name)

    # Run all updates concurrently
    tasks = (update(channel_id) for channel_id in temp_channel_ids)
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        bot.logger.debug(f"Unhandled error in func update_channel_name_and_control_msg {e}")

    end = time.perf_counter()
    duration = end - start
    bot.logger.debug(f"Temp channel name update completed in {duration:.4f} seconds")
