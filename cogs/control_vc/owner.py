from cogs.control_vc.embed_updates import update_info_embed


async def is_owner(view, interaction):
    if not interaction.user in interaction.channel.members:
        view.bot.logger.debug(f"User ({interaction.user}) interacted with control message that they are not connected to.")
        await interaction.response.send_message(f"You are not connected to this voice channel {interaction.user.mention}!", ephemeral=True, delete_after=15)
        return False

    owner_id = view.bot.db.get_temp_channel_info(interaction.channel.id).owner_id
    if owner_id is None:
        view.bot.db.set_owner_id(interaction.channel.id, interaction.user.id)
        await update_info_embed(view.bot, interaction.channel)
        return True
    elif owner_id != interaction.user.id:
        view.bot.logger.debug(f"User ({interaction.user}) interacted with control message that they don't own.")
        await interaction.response.send_message(f"You do not own this temporary channel {interaction.user.mention}!", ephemeral=True, delete_after=15)
        return False
    else:
        return True
