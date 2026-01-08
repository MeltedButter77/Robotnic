import discord


async def close(bot):
    bot.logger.info(f'Logging out {bot.user}')

    # Update all control messages with a disabled button saying its expired
    for temp_channel_id in bot.db.get_temp_channel_ids():
        temp_channel = bot.get_channel(temp_channel_id)
        # Searches first 10 messages for first send by the bot. This will almost always be the creator
        async for control_message in temp_channel.history(limit=10, oldest_first=True):
            if control_message.author.id == bot.user.id:
                # Create a new view with one disabled button
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="This control message has expired",
                        style=discord.ButtonStyle.secondary,
                        disabled=True
                    )
                )
                # Edit the message to show the new view
                await control_message.edit(view=view)

    await bot.send_bot_log(type="stop", message=f"Bot {bot.user.mention} stopping.")
    await super().close()