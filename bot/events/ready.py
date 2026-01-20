from bot.logging import BotLogService, GuildLogService
from bot.tasks import background


async def on_ready(bot):
    if bot.ready:
        await bot.BotLogService.send("reconnect", "Bot Reconnected")
        return

    # Set services that require channels to already be cached
    bot.BotLogService = BotLogService(bot)
    bot.GuildLogService = GuildLogService(bot)

    # Start background tasks
    await background.create_tasks(bot)

    # Login notification
    bot.logger.info(f"Logged in as {bot.user}")
    await bot.BotLogService.send(event="start", message=f"Bot {bot.user.mention} started.")

    # Sync commands and nofity
    await bot.sync_commands()
    bot.logger.info(f'Commands synced')
    await bot.BotLogService.send(event="start", message=f"Commands synced.")

