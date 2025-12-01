import discord
from discord.ext import commands


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


class GeneralCCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(description="Responds with bot latency.")
    @discord.default_permissions(administrator=True)
    async def ping(self, ctx):
        await ctx.respond(f"Pong! Latency is {self.bot.latency}")

    @discord.slash_command(description="Get support using Robotnic or support the creator.")
    async def support(self, ctx):
        embeds = [
            DonateEmbed()
        ]
        await ctx.respond(f"{ctx.user.mention}", embeds=embeds, view=ButtonsView())

    # Aliases to /support
    @discord.slash_command(description="Get help using Robotnic or support the creator.")
    async def help(self, ctx):
        await self.support.callback(self, ctx)

    @discord.slash_command(description="Support the creator of Robotnic.")
    async def donate(self, ctx):
        await self.support.callback(self, ctx)


def setup(bot):
    bot.add_cog(GeneralCCog(bot))
