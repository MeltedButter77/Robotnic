import discord


class ButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.create_items()

    def create_items(self):
        self.add_item(
            discord.ui.Button(
                label="Support the Developer",
                url="https://github.com/sponsors/MeltedButter77",
                emoji="💖",
                style=discord.ButtonStyle.link
            )
        )
        self.add_item(
            discord.ui.Button(
                label="Discord Support Server",
                url="https://discord.gg/rcAREJyMV5",
                emoji="🔧",
                style=discord.ButtonStyle.link
            )
        )
