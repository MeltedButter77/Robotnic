import discord


class ChannelControlsEmbed(discord.Embed):
    def __init__(self):
        super().__init__(
            title="Select Options",
            color=discord.Color.blue()
        )
        self.description = f"This menu allows for editing server settings."
        self.add_field(name="", value="", inline=False)

