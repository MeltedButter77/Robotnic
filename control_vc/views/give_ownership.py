import discord
from control_vc.embed_updates import update_info_embed


class GiveOwnershipView(discord.ui.View):
    def __init__(self, bot, channel):
        super().__init__(timeout=60)
        self.bot = bot
        self.channel = channel
        self.message = None

        class SelectUserMenu(discord.ui.Select):
            def __init__(self, bot, channel):
                self.bot = bot
                self.channel = channel

                owner_id = self.bot.db.get_temp_channel_info(channel.id).owner_id

                options = []
                options.append(
                    discord.SelectOption(
                        label=f"Noone (allows anyone to claim)",
                        description=f"",
                        value=f"None",
                        emoji="❌"
                    )
                )
                for member in channel.members:
                    if member.id == owner_id:
                        continue
                    options.append(
                        discord.SelectOption(
                            label=f"{member.display_name}",
                            description=f"",
                            value=f"{member.id}",
                            emoji="👥"
                        )
                    )

                super().__init__(placeholder="Select user to transfer ownership to", options=options, min_values=1, max_values=1)

            async def callback(self, interaction: discord.Interaction):
                owner_perms = {'connect': True, 'view_channel': True}
                if self.values[0] == "None":
                    selected_member = None

                    embed = discord.Embed(
                        title="Channel available to Claim!",
                        description=f"Ownership of your channel has been removed.",
                        color=0x00ff00
                    )
                    embed.set_footer(text="This message will disappear in 20 seconds.")
                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)

                    self.bot.db.set_owner_id(self.channel.id, None)

                    await update_info_embed(self.bot, self.channel)

                else:
                    selected_member = interaction.guild.get_member(int(self.values[0]))

                if selected_member:
                    await self.channel.set_permissions(
                        selected_member,
                        **owner_perms
                    )

                    self.bot.db.set_owner_id(self.channel.id, selected_member.id)
                    await update_info_embed(self.bot, self.channel)

                    embed = discord.Embed(
                        title="Transferred!",
                        description=f"Ownership of your channel was successfully transferred to {selected_member.mention}.",
                        color=0x00ff00
                    )
                    embed.set_footer(text="This message will disappear in 20 seconds.")
                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)

                    embed = discord.Embed(
                        title="Channel Ownership",
                        description=f"You now own this channel! Use the above buttons to manage it as you wish.",
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text="This message will disappear in 60 seconds.")
                    await self.channel.send(f"{selected_member.mention}", embed=embed, delete_after=60)

        self.add_item(SelectUserMenu(bot, self.channel))

    async def send_initial_message(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎁 Who would you like to give your channel to?",
            description=f"You have 60 seconds to select one member.",
            footer=discord.EmbedFooter("You have 60 seconds to select an option."),
            color=0x00ff00
        )
        self.message = await interaction.followup.send(embed=embed, view=self, ephemeral=True, wait=True)  # wait ensures that self.message is set before continuing

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass
