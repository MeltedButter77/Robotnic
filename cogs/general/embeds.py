import discord


class DonateEmbed(discord.Embed):
    def __init__(self):
        super().__init__()
        self.color = discord.Color.green()
        self.title = "💚 A Message from the Developer"
        self.description = (
            "Thank you for using Robotnic! 🤖\n"
            "This is a **[FOSS](<https://wikipedia.org/wiki/Free_and_open-source_software>)** project with a **free** public instance developed and hosted by "
            "[MeltedButter77](https://github.com/MeltedButter77)."
        )
        self.add_field(
            name="💸 Donations",
            value=(
                "Robotnic took a long time to develop and also **costs money to host**, "
                "which MeltedButter currently pays out of his own pocket."
            ),
            inline=False
        )
        self.add_field(
            name="🙏 Please Consider Supporting the Developer",
            value="Every bit of support helps keep Robotnic running smoothly. ❤️",
            inline=False
        )
        self.set_footer(text="📩 Need more help? Reach out to support below!")
