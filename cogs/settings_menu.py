import discord
from discord.ui import View, Select, Button, Modal, InputText
from discord.ext import commands


class SettingsMenuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(description="Change Guild Settings")
    @discord.default_permissions(administrator=True)
    async def settings(self, ctx):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send_response(f"Sorry {ctx.author.mention}, you require the `administrator` permission to run this command.")

        view = SettingsView(ctx=ctx, bot=self.bot)
        message = await ctx.send_response(f"{ctx.author.mention}", embed=MessageEmbed(), view=view)  # , ephemeral=True)
        view.message = message


def setup(bot):
    bot.add_cog(SettingsMenuCog(bot))


class MessageEmbed(discord.Embed):
    def __init__(self, is_advanced: bool = False):
        super().__init__(
            title="Guild (Server) Settings",
            color=discord.Color.blue()
        )

        self.add_field(name="field title", value="field desc", inline=False)


class SettingsView(View):
    def __init__(self, ctx, bot):
        super().__init__()
        self.bot = bot
        self.message = None
        self.author = ctx.author

        self.create_items(ctx.guild)

    def create_items(self, guild=None):
        # We require the guild id to edit the relevant settings.
        # Usually provided by ctx on creation but when updated the guild is from the associated message.
        if not guild and self.message:
            guild = self.message.guild

        if guild is None:
            self.bot.logger.error("No guild obj to create items for SettingsView")
            return



        # Dropdown
        controls_options = [
            discord.SelectOption(value="rename", label="Rename Channel", emoji="🏷️", default=True),
            discord.SelectOption(value="limit", label="Edit User Limit", emoji="🚧", default=True),
            discord.SelectOption(value="clear", label="Clear Messages", emoji="🧽", default=True),
            discord.SelectOption(value="ban", label="Ban Users or Roles", emoji="🔨", default=True),
            discord.SelectOption(value="give", label="Give Ownership", emoji="🎁", default=True),
            discord.SelectOption(value="delete", label="Delete Channel", emoji="🗑️", default=True),
        ]
        controls_select = Select(placeholder="Select options to Enable or Disable", options=controls_options, max_values=len(controls_options), min_values=0)
        controls_select.callback = self.controls_select_callback
        self.add_item(controls_select)

    async def update(self):
        self.clear_items()
        self.create_items()
        await self.message.edit(view=self, embeds=self.message.embeds)

    # Dropdown callback
    async def controls_select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(f"This is not your menu!", ephemeral=True)

        await interaction.response.send_message("hey")
        await self.update()

    async def on_timeout(self):
        await self.message.edit(view=None, embeds=[], content="> Message timed out. Please run the command again.")
