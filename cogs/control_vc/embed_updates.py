from cogs.control_vc.embeds import ChannelInfoEmbed


async def update_info_embed(bot, channel, title=None, user_limit=None):
    control_message = None
    async for message in channel.history(limit=1, oldest_first=True):
        control_message = message
    if control_message is None:
        print("Failed to find control message")
        return
    embeds = control_message.embeds
    embeds[1] = ChannelInfoEmbed(bot, channel, title, user_limit)
    await control_message.edit(embeds=embeds)
