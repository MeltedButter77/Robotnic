import discord


class OptionsEmbed(discord.Embed):
    def __init__(self):
        super().__init__(
            title="Creator Channels' Options",
            color=discord.Color.blue()
        )
        self.set_footer(text="This message will disappear in 120 seconds")
        self.add_field(name="Child Name", value="This is the pattern the created channel's names will follow\n> Available Variables: `{user}`, `{count}` & `{activity}`", inline=False)
        self.add_field(name="User Limit", value="The user limit set on created channels\n> `0` = Unlimited\n> Accepts any integer `0`-`99` inclusive", inline=False)
        self.add_field(name="Permissions", value="Whether the created channels should have the same permissions as the creator, category or none at all", inline=False)
        self.add_field(name="Category", value="Which category created channels are placed in\n> If blank, will use the same as the creator", inline=False)


class ListCreatorsEmbed(discord.Embed):
    def __init__(self, guild, bot):
        super().__init__(
            title="Selected Options for each Creator Channel",
            color=discord.Color.green()
        )

        # Creates a field for each creator channel
        creator_channel_ids = bot.repos.creator_channels.get_ids(guild_id=guild.id)
        for i, channel_id in enumerate(creator_channel_ids):
            channel = bot.get_channel(channel_id)
            creator_info = bot.repos.creator_channels.get_info(channel_id)

            if channel:
                child_name = creator_info.child_name
                user_limit = "Unlimited" if creator_info.user_limit == 0 else creator_info.user_limit
                category = "Same as Creator" if creator_info.child_category_id == 0 else bot.get_channel(creator_info.child_category_id)
                if creator_info.child_overwrites == 1:
                    overwrites = "From Creator channel"
                elif creator_info.child_overwrites == 2:
                    overwrites = "From category"
                else:  # should be for case 0
                    overwrites = "None. Permissions are cleared"

                desc = f"Naming Scheme:\n> `{child_name}`\nUser Limit:\n> `{user_limit}`\nPermission Inheritance:\n> `{overwrites}`\nCategory:\n> `{category}`"
                self.add_field(name=f"#{i+1}. {channel.mention}", value=desc, inline=True)

        # Handle case of no fields. Also prevents error of no embed content
        if len(self.fields) < 1:
            self.title = "No Creators to list. Make a new one below."
