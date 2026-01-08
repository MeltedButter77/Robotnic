import discord


class MessageEmbed(discord.Embed):
    def __init__(self, is_advanced: bool = False):
        super().__init__(
            title="Guild (Server) Settings",
            color=discord.Color.blue()
        )
        self.description = f"This menu allows for editing server settings."

        self.add_field(name="1st row Menu", value="Handles which voice controls are avalible to the owner of a temp channel", inline=False)
        self.add_field(name="2nd row Menu", value="Used to set a logs channel. This allows admins to store who owned channels named what and when. It stores who created a channel and who manually changes its name and to what. Activity based tracking is a wip.", inline=False)
        self.add_field(name="3srd row Button", value="Clears the logs channel", inline=False)
