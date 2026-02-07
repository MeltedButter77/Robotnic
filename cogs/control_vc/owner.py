from cogs.control_vc.embed_updates import update_info_embed


async def is_owner(view, interaction):
    if not interaction.user in interaction.channel.members:
        view.bot.logger.debug(f"User ({interaction.user}) interacted with control message that they are not connected to.")
        await interaction.response.send_message(f"You are not connected to this voice channel {interaction.user.mention}!", ephemeral=True, delete_after=15)
        return False

    connected_user_ids = []
    for user in interaction.channel.members:
        connected_user_ids.append(user.id)

    owner_id = view.bot.repos.temp_channels.get_temp_channel_info(interaction.channel.id).owner_id

    # If owner isn't connected. Make interacting user owner and continue
    if owner_id is None or owner_id not in connected_user_ids:
        view.bot.repos.temp_channels.set_owner_id(interaction.channel.id, interaction.user.id)

    # If owner is connected and isn't interacting user return false
    elif owner_id != interaction.user.id:
        view.bot.logger.debug(f"User ({interaction.user}) interacted with control message that they don't own.")
        await interaction.response.send_message(f"You do not own this temporary channel {interaction.user.mention}!", ephemeral=True, delete_after=15)
        return False

    # Update embed and return True meaning interacting user is owner
    await update_info_embed(view.bot, interaction.channel)
    return True
