from bot.tasks import background


async def on_ready(bot):
    # Start background tasks
    await background.create_tasks(bot)

    # Login notification
    bot.logger.info(f"Logged in as {bot.user}")
    await bot.send_bot_log(type="start", message=f"Bot {bot.user.mention} started.")

    # Sync commands and nofity
    await bot.sync_commands()
    bot.logger.info(f'Commands synced')
    await bot.send_bot_log(type="start", message=f"Commands synced.")

