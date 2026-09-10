import discord


class DonateEmbed(discord.Embed):
    def __init__(self):
        super().__init__()
        self.color = discord.Color.green()
        self.title = "💚 Thank you for using Robotnic!"
        self.description = (
            "\n"
            "This bot as a **[FOSS](<https://wikipedia.org/wiki/Free_and_open-source_software>)** project with a **free** to use public instance, however this **costs money**. Current donations do not even cover hosting costs."
        )
        self.add_field(
            name="💸 Please Consider Supporting through Ko-fi!",
            value="",
            inline=False
        )


class HelpEmbed(discord.Embed):
    def __init__(self):
        super().__init__()
        self.color = discord.Color.green()
        self.title = "Command List"
        self.description = (
        )
        self.add_field(
            name="1️⃣ /setup",
            value=(
                "Use this menu to create new `Creator Channel`s by clicking the green \"Make new Creator\" button or edit existing `Creator Channel`s using the dropdown list."
            ),
            inline=False
        )
        self.add_field(
            name="2️⃣ /settings controls",
            value="Allows changing the controls available to channel owners. Every button is togglable and you can choose between labeled buttons, icons or a dropdown menu as controls. You can also adjust if the owner gets pinged on channel creation.",
            inline=False
        )
        self.add_field(
            name="3️⃣ /settings logging",
            value="Allows for setting a log channel, if set, selected events will be logged in that channel. To customise the list, simply deselect the ones you would not like to include.",
            inline=False
        )
        self.add_field(
            name="4️⃣ /settings profanity_filter",
            value="While still basic, this setting allows for disabling or only sending an alert if the profanity filter is triggered rather than blocking the action.",
            inline=False
        )
        self.add_field(
            name="5️⃣ /settings dm-owner",
            value="Enable or disable DMing channel owners when they create a temporary channel. Defaults to on.",
            inline=False
        )
        self.add_field(
            name="6️⃣ /donate | /support | /website",
            value="Returns with information on how to support Robotnic's uptime.",
            inline=False
        )
        self.set_footer(text="📩 Need more help? Reach out to support below!")