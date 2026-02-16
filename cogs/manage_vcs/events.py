from cogs.manage_vcs.lifecycle import create_on_join, delete_on_leave
from cogs.manage_vcs.update_name import update_channel_name_and_control_msg


async def handle_voice_state_update(bot, member, before, after):
    # Filter out normal updates when not switching channels
    if before is not None and after is not None:
        if before.channel == after.channel:
            return

    if after.channel:  # If a user joined a channel
        creator_channel_ids = bot.repos.creator_channels.get_ids()
        if after.channel.id in creator_channel_ids:  # Filter to creator channels
            await create_on_join(member, before, after, bot)

    if before.channel:  # If a user left a channel
        temp_channel_ids = bot.repos.temp_channels.get_ids(guild_id=before.channel.guild.id)
        if before.channel.id in temp_channel_ids:  # Filter to temp channels
            await delete_on_leave(member, before, after, bot)

            # Update channel names of all temp channels in the guild
            # Technically channel names only need to be updated on activity change and deleting a channel (this), no background task required.
            bot.logger.debug(f"Updating temp channel names in a guild because a user left a temp_vc")
            await update_channel_name_and_control_msg(bot, temp_channel_ids)


async def handle_presence_update(bot, before, after):
    if not hasattr(after, "channel"):
        return
    temp_channel = after.channel

    bot.logger.debug(f"Updating {temp_channel.name} due to activity change")
    await update_channel_name_and_control_msg(bot, [temp_channel.id])
