import discord
from cogs.control_vc.enums import ChannelState
from cogs.manage_vcs.create_name import create_temp_channel_name


class ControlIconsEmbed(discord.Embed):
    def __init__(self, bot):
        super().__init__(
            title="",
            description="",
            color=0x00ff00
        )

        self.add_field(name="🏷️ Rename", value="", inline=True)
        self.add_field(name="🚧 Limit", value="", inline=True)
        self.add_field(name="🎁 Give", value="", inline=True)
        self.add_field(name="🧽 Clear", value="", inline=True)
        self.add_field(name="🔨 Ban", value="", inline=True)
        self.add_field(name="🗑️ Delete", value="", inline=True)
        if bot.settings["control_message"].get("state_changeable", False):
            self.add_field(name="🌐 Public", value="", inline=True)
            self.add_field(name="🙈 Hide", value="", inline=True)
            self.add_field(name="🔒 Lock", value="", inline=True)


class ChannelInfoEmbed(discord.Embed):
    def __init__(self, bot, temp_channel, title=None, user_limit=None):
        super().__init__(
            color=discord.Color.blue()
        )

        temp_channel_info = bot.repos.temp_channels.get_temp_channel_info(temp_channel.id)

        # title input incase it was just changed and propagated to channel yet
        self.title = title
        if not self.title:
            is_renamed = temp_channel_info.is_renamed
            if is_renamed:
                self.title = f"{temp_channel.name}"
            else:
                self.title = create_temp_channel_name(bot, temp_channel)

        self.footer = discord.EmbedFooter("Channel Name will update as quickly as Discord Allows.")

        owner_id = temp_channel_info.owner_id
        if owner_id:
            if owner_id is not None:
                owner = f"<@{owner_id}>"
            else:
                owner = "None, available to claim"
        else:
            owner = "None, available to claim"
        self.add_field(name="Owner", value=f"{owner}", inline=True)

        if not user_limit:
            user_limit = temp_channel.user_limit
        if user_limit == 0:
            user_limit = "♾️ Unlimited"
        self.add_field(name="User Limit", value=f"{user_limit}", inline=True)

        # region = temp_channel.rtc_region
        # if region is None:
        #     region = "🌍 Auto"
        # self.add_field(name="Region", value=f"{region}", inline=True)

        if bot.settings["control_message"].get("state_changeable", False):
            channel_state_id = temp_channel_info.channel_state
            if channel_state_id == ChannelState.PUBLIC.value:
                channel_state = "🌐 Public"
            elif channel_state_id == ChannelState.LOCKED.value:
                channel_state = "🔒 Locked"
            elif channel_state_id == ChannelState.HIDDEN.value:
                channel_state = "🙈 Hidden"
            else:
                channel_state = "None"
            self.add_field(name="Access", value=f"{channel_state}", inline=True)