from manage_vcs.lifecycle import create_on_join, delete_on_leave
from manage_vcs.update_name import update_channel_name_and_control_msg


async def handle_voice_state_update(bot, member, before, after):
    # Filter out normal updates when not switching channels
    if before is not None and after is not None:
        if before.channel == after.channel:
            return

    if after.channel:  # If a user joined a channel
        creator_channel_ids = bot.db.get_creator_channel_ids()
        if after.channel.id in creator_channel_ids:  # Filter to creator channels
            await create_on_join(member, before, after, bot)

    if before.channel:  # If a user left a channel
        temp_channel_ids = bot.db.get_temp_channel_ids()
        if before.channel.id in temp_channel_ids:  # Filter to temp channels
            await delete_on_leave(member, before, after, bot)

            # Update channel names of all temp channels
            # Technically channel names only need to be updated on activity change and deleting a channel (this), no coroutine needed.
            # Future optimisation, This should also only update channels in this server
            bot.logger.debug(f"Updating all temp channel names because a user left a temp_vc")
            temp_channel_ids = bot.db.get_temp_channel_ids()
            await update_channel_name_and_control_msg(bot, temp_channel_ids)


async def handle_presence_update(bot, before, after):
    if not hasattr(after, "channel"):
        return
    temp_channel = after.channel

    bot.logger.debug(f"Updating {temp_channel.name} due to activity change")
    await update_channel_name_and_control_msg(bot, [temp_channel.id])
