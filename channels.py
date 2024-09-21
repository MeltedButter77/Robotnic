from unicodedata import category

import discord
from discord.ext import commands
import json

# Load the token from config.json
with open('config.json') as config_file:
    config = json.load(config_file)
channel_hub_id = config["channel_hub_id"]
temp_channels = {}


class Channels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        guild = member.guild
        if after.channel:
            channel_hub = discord.utils.get(guild.voice_channels, id=channel_hub_id)

            # Creates Temp Channel
            if after.channel.id == channel_hub.id:
                values = temp_channels.values()
                channel_number = 1
                for i, value in enumerate(sorted(values)):
                    if not value == i+1:
                        channel_number = i+1
                        break
                    channel_number = value + 1

                channel = await guild.create_voice_channel(category=channel_hub.category, name="Lobby " + f"{channel_number}")
                temp_channels[channel.id] = channel_number

                await member.move_to(channel)

        # Deletes Temp Channel
        if before.channel:
            if not after.channel in temp_channels and before.channel.id in temp_channels:
                left_channel = discord.utils.get(guild.voice_channels, id=before.channel.id)
                if len(left_channel.members) == 0:
                    temp_channels.pop(left_channel.id)
                    await left_channel.delete()


async def setup(bot):
    await bot.add_cog(Channels(bot))
