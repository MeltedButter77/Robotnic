

async def create_on_join(member, before, after, bot, logger):
    logger.debug(f"{member} joined creator channel {after.channel}")

    # Logic flow:
    # 1. Retrieve child settings from db
    # 2. Get category & overwrites, both depend on settings
    # 3. Create channel & move user
    # 4. Create name
    # 5. Edit channel w correct name & overwrites and disable permission sync

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

    new_temp_channel = await creator_channel.guild.create_voice_channel(
        name="⌛",
        category=category,
        overwrites=overwrites,
    )
    bot.db.add_temp_channel(new_temp_channel.guild.id, new_temp_channel.id, creator_channel.id, member.id, 0, 1, False)

    try:
        await member.move_to(new_temp_channel)
        logger.debug(f"Moved {member} to {new_temp_channel}")
    except Exception as e:
        logger.debug(f"Error creating voice channel, handled. {e}")
        bot.db.remove_temp_channel(new_temp_channel.id)
        await new_temp_channel.delete()

    child_name_template = db_creator_channel_info.child_name

    channel_name = child_name_template
    if "{user}" in str(child_name_template):
        member_name = member.nick if member.nick else member.display_name
        channel_name = channel_name.replace("{user}", member_name)

    # Max char is 100, using 98 just in case
    if len(str(channel_name)) > 95:
        channel_name = channel_name[:95] + "..."

    # Disable sync and reapply overwrites. this is because creating a channel in a
    # category with no overwrites will auto get overwrites of the category even if
    # {} is passed in overwrites
    try:
        await new_temp_channel.edit(
            name=channel_name,
            user_limit=db_creator_channel_info.user_limit,
            sync_permissions=False,
            overwrites=overwrites
        )
    except Exception as e:
        logger.debug(f"Error finalizing creation of voice channel, handled. {e}")
        bot.db.remove_temp_channel(new_temp_channel.id)


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
