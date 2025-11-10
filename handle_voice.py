

async def user_join(member, before, after, bot, logger):
    logger.debug(f"{member} joined {after.channel}")


async def user_move(member, before, after, bot, logger):
    logger.debug(f"{member} moved from {before.channel} to {after.channel}")


async def user_leave(member, before, after, bot, logger):
    logger.debug(f"{member} left {before.channel}")
