import discord


class OptionsEmbed(discord.Embed):
    def __init__(self, is_advanced: bool = False):
        super().__init__(
            title="Creator Channels' Options",
            color=discord.Color.blue()
        )

        self.add_field(name="1. Child Name", value="This is the pattern the created channel's names will follow\n> Available Variables: `{user}`, `{count}` & `{activity}`\n> (Default: `{user}'s Room`)", inline=False)
        if is_advanced:
            self.add_field(name="2. User Limit", value="The user limit set on created channels\n> `0` = Unlimited\n> Accepts any integer `0`-`99` inclusive (Default: `0`)", inline=False)
            self.add_field(name="3. Category", value="Which category created channels are placed in\n> `0` = Same as creator\n> Accepts category ID as input (Default: `0`)", inline=False)
            self.add_field(name="4. Permissions", value="Whether the created channels should have the same permissions as the creator, category or none at all\n> `0` = No Permissions\n> `1` = Creator Channel\n> `2` = Relevant Category\n> Accepts integers `0`-`2` inclusive (Default: `1`)", inline=False)
        else:
            self.add_field(name="For more Options, use `/setup_advanced` instead", value="", inline=False)


class ListCreatorsEmbed(discord.Embed):
    def __init__(self, guild, bot, is_advanced: bool = False):
        super().__init__(
            title="Selected Options for each Creator Channel",
            color=discord.Color.green()
        )

        # Creates a field for each creator channel
        creator_channel_ids = bot.repos.creator_channels.get_creator_channel_ids(guild_id=guild.id)
        for i, channel_id in enumerate(creator_channel_ids):
            channel = bot.get_channel(channel_id)
            creator_info = bot.repos.creator_channels.get_creator_channel_info(channel_id)

            if channel:
                child_name = creator_info.child_name
                user_limit = "0 = Unlimited" if creator_info.user_limit == 0 else creator_info.user_limit

                category = "0 = Same as Creator" if creator_info.child_category_id == 0 else creator_info.child_category_id

                if creator_info.child_overwrites == 1:
                    overwrites = "1 = From Creator channel"
                elif creator_info.child_overwrites == 2:
                    overwrites = "2 = From category"
                else:  # should be for case 0
                    overwrites = "0 = None. Permissions are cleared"

                if is_advanced:
                    desc = f"Names of Created Channels:\n> `{child_name}`\nUser Limit:\n> `{user_limit}`\nCategory:\n> `{category}`\nPermission Inheritance:\n> `{overwrites}`"
                else:
                    desc = f"Name Scheme:\n> `{child_name}`"
                self.add_field(name=f"#{i+1}. {channel.mention}", value=desc, inline=True)

        if not is_advanced:
            self.add_field(name="For more Options, use `/setup_advanced` instead", value="", inline=False)

        # Handle case of no fields. Also prevents error of no embed content
        if len(self.fields) < 1:
            self.title = "No Creators to list. Make a new one below."
