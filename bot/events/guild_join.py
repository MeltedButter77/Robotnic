import discord


async def on_guild_join(self, guild):
    # This event is triggered when the bot joins a new guild
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title=f"Hello {guild.name}! 🎉",
                description="Thank you for inviting me to your server! 😊\nHere are the commands to get started.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="/setup",
                value="Allows an admin to setup a channel creator (or channel hub) which dynamically creates voice channels when users join them.",
                inline=False
            )
            embed.add_field(
                name="/setup_advanced",
                value="Same as /setup except it allows more customisation. Change name, user limits, category of created channels and the permissions",
                inline=False
            )
            embed.set_footer(text="Need more help? Reach out to support below!")
            view = discord.ui.View()
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.url,
                                            label="Contact Support",
                                            url=f"https://discord.gg/rcAREJyMV5"))
            # view.add_item(discord.ui.Button(style=discord.ButtonStyle.url,
            #                                 label="Visit Website",
            #                                 url=f"link"))
            await channel.send("Thanks for inviting me!", embed=embed, view=view)
            break

    # Create the embed with the server information
    embed = discord.Embed(
        title="Joined a New Server!",
        description=f"",
        color=discord.Color.green()
    )
    embed.add_field(name="Server Name", value=guild.name, inline=True)
    embed.add_field(name="Server ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=f"{guild.owner} (ID: {guild.owner_id})", inline=True)
    embed.add_field(name="Member Count", value=guild.member_count, inline=True)
    embed.add_field(name="Creation Date", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Region/Locale", value=str(guild.preferred_locale), inline=True)
    await self.BotLogService.send(event="guild_join", message=f"", embeds=[embed])