import datetime
import discord
from cogs.control_vc.views.control_view import ControlView
from cogs.manage_vcs.create_name import create_temp_channel_name


async def create_on_join(member, before, after, bot):
    bot.logger.debug(f"{member} joined creator channel {after.channel}")

    # Logic flow:
    # 1. Retrieve child settings from db
    # 2. Get category & overwrites, both depend on settings
    # 3. Create channel & move user
    # 4. Create name
    # 5. Edit channel w correct name & overwrites and disable permission sync
    # 6. Send logs and notifications messages

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

    db_creator_channel_info = bot.repos.creator_channels.get_info(creator_channel.id)
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

    overwrites[bot.user] = discord.PermissionOverwrite(
        view_channel=True,
        manage_channels=True,
        send_messages=True,
        manage_messages=True,
        read_message_history=True,
        connect=True,
        move_members=True,
    )
    overwrites[member] = discord.PermissionOverwrite(
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        connect=True,
    )

    try:
        new_temp_channel = await creator_channel.guild.create_voice_channel(
            name="⌛",
            category=category,
            overwrites=overwrites,
            position=creator_channel.position,
        )
    except discord.Forbidden as e:
        bot.logger.warning(
            "Missing permissions while creating temp channel",
            extra={
                "guild_id": creator_channel.guild.id,
                "channel_id": creator_channel.id,
            },
        )

        embed = discord.Embed()
        embed.add_field(name="Required",
                        value="`view_channel`, `manage_channels`, `send_messages`, `manage_messages`, `read_message_history`, `connect`, `move_members`")
        await creator_channel.send(
            f"Sorry {member.mention}, I require the following permissions. Make sure they are not overwritten by the category (In this case `{category.name}`).",
            embed=embed, delete_after=300)
        return

    counts = bot.repos.temp_channels.get_counts(creator_channel.id)
    if len(counts) < 1:
        count = 1
    else:
        count = max(counts) + 1

    bot.repos.temp_channels.add(new_temp_channel.guild.id, new_temp_channel.id, creator_channel.id, member.id, 0, count, False)

    try:
        await member.move_to(new_temp_channel)
        bot.logger.debug(f"Moved {member} to {new_temp_channel}")
    except Exception as e:
        bot.logger.debug(f"Error creating voice channel, most likely a quick join and leave. Handled. {e}")
        bot.repos.temp_channels.remove(new_temp_channel.id)
        await new_temp_channel.delete()
        return

    channel_name = create_temp_channel_name(bot, new_temp_channel, db_creator_channel_info=db_creator_channel_info)

    # Disable sync and reapply overwrites. this is because creating a channel in a
    # category with no overwrites will auto get overwrites of the category even if
    # {} is passed in overwrites
    try:
        # Could use bot.renamer to avoid rate-limit problems
        await new_temp_channel.edit(
            name=channel_name,
            user_limit=db_creator_channel_info.user_limit,
            sync_permissions=False,
            overwrites=overwrites
        )

        # Send control message in channel chat
        view = ControlView(bot, new_temp_channel)
        print("good1")
        await view.send_initial_message(member, channel_name=channel_name)
        print("good2")
    except Exception as e:
        bot.logger.debug(f"Error finalizing creation of voice channel, handled. {e}")
        bot.repos.temp_channels.remove(new_temp_channel.id)

    # Sends messages in the guild log channel and the bot's notification channel - uses get_guild_logs_channel_id instead of get_guild_settings for read efficiency
    embed = discord.Embed(
        title="TempChannel Create",
        description="",
        color=discord.Color.green()
    )
    embed.add_field(name="Channel",
                    value=f"`{new_temp_channel.name}` (`{new_temp_channel.id}`)",
                    inline=False)
    embed.add_field(name="User",
                    value=f"`{member.display_name}` (`{member.display_name}`, `{member.id}`)",
                    inline=False)
    embed.timestamp = datetime.datetime.now()
    await bot.GuildLogService.send(event="channel_create", guild=after.channel.guild, message=f"", embed=embed)
    await bot.BotLogService.send(event="channel_create", message=f"Temp Channel (`{new_temp_channel.name}`) was made in server (`{member.guild.name}`) by user (`{member}`)")


async def delete_on_leave(member, before, after, bot):
    old_temp_channel = before.channel

    if len(old_temp_channel.members) < 1:
        bot.logger.debug(f"Left temp channel is empty. Deleting...")

        try:
            await old_temp_channel.delete()
            bot.repos.temp_channels.remove(old_temp_channel.id)
            bot.logger.debug(f"Deleted {old_temp_channel.name}")

        except discord.NotFound as e:
            bot.repos.temp_channels.remove(old_temp_channel.id)
            bot.logger.debug(f"Channel not found removing entry in db, handled. {e}")
            return

        except discord.Forbidden as e:
            bot.logger.debug(
                f"Permission error removing temp channel, handled by sending a message notifying of lack of perms. {e}")
            await old_temp_channel.send(f"Sorry {member.mention}, I do not have permission to delete this channel.", delete_after=300)
            return

        except Exception as e:
            bot.logger.error(f"Unknown error removing temp channel. {e}")
            return

        embed = discord.Embed(
            title="TempChannel Removed",
            description="",
            color=discord.Color.orange()
        )
        embed.add_field(name="Channel",
                        value=f"`{old_temp_channel.name}` (`{old_temp_channel.id}`)",
                        inline=False)
        embed.add_field(name="Last Connected User",
                        value=f"`{member.display_name}` (`{member.display_name}`, `{member.id}`)",
                        inline=False)
        embed.timestamp = datetime.datetime.now()
        await bot.GuildLogService.send(event="channel_remove", guild=member.guild, message=f"", embed=embed)
        await bot.BotLogService.send(event="channel_remove", message=f"Temp Channel was removed in server (`{member.guild.name}`) by user (`{member}`)")
