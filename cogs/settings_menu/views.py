import discord
from discord.ui import View, Select, Button, Modal, InputText


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

        guild_settings = self.bot.repos.guild_settings.get(guild.id)
        enabled_controls = guild_settings["enabled_controls"]

        # Dropdown
        controls_options = [
            discord.SelectOption(value="rename", label="Rename Channel", emoji="🏷️", default="rename" in enabled_controls),
            discord.SelectOption(value="limit", label="Edit User Limit", emoji="🚧", default="limit" in enabled_controls),
            discord.SelectOption(value="clear", label="Clear Messages", emoji="🧽", default="clear" in enabled_controls),
            discord.SelectOption(value="ban", label="Ban Users or Roles", emoji="🔨", default="ban" in enabled_controls),
            discord.SelectOption(value="give", label="Give Ownership", emoji="🎁", default="give" in enabled_controls),
            discord.SelectOption(value="delete", label="Delete Channel", emoji="🗑️", default="delete" in enabled_controls),
        ]
        controls_select = Select(placeholder="Select options to Enable or Disable", options=controls_options, max_values=len(controls_options), min_values=0)
        controls_select.callback = self.controls_select_callback
        self.add_item(controls_select)

        logs_channel = guild.get_channel(guild_settings["logs_channel_id"])
        if logs_channel:
            logs_channel_name = f"#{logs_channel.name}"
        else:
            logs_channel_name = "Not Set"

        log_channel_select = discord.ui.Select(
            select_type=discord.ComponentType.channel_select,
            channel_types=[discord.ChannelType.text],
            placeholder=f"Current: {logs_channel_name} - Select a new channel",
        )
        log_channel_select.callback = self.log_channel_select_callback
        self.add_item(log_channel_select)

        remove_logs_channel_button = discord.ui.Button(
            label="Clear Logs Channel",
            style=discord.ButtonStyle.danger
        )
        remove_logs_channel_button.callback = self.remove_logs_channel_button_callback
        self.add_item(remove_logs_channel_button)

    async def log_channel_select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(f"This is not your menu!", ephemeral=True)

        channel_id = interaction.data["values"][0]
        self.bot.repos.guild_settings.edit(interaction.guild_id, logs_channel_id=channel_id)
        channel = self.message.guild.get_channel(int(channel_id))

        await self.update()
        return await interaction.response.send_message(f"Saved! {channel.mention} is now the log channel.", ephemeral=True, delete_after=5)

    async def controls_select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(f"This is not your menu!", ephemeral=True)
        enabled_controls = interaction.data["values"]
        self.bot.repos.guild_settings.edit(interaction.guild_id, enabled_controls=enabled_controls)
        await self.update()
        return await interaction.response.send_message(f"Options Saved!", ephemeral=True, delete_after=5)

    async def remove_logs_channel_button_callback(self, interaction):
        self.bot.repos.guild_settings.edit(interaction.guild_id, logs_channel_id=0)
        await self.update()
        await interaction.response.send_message("Cleared logs channel!", ephemeral=True, delete_after=5)

    async def update(self):
        self.clear_items()
        self.create_items()
        await self.message.edit(view=self, embeds=self.message.embeds)

    async def on_timeout(self):
        await self.message.edit(view=None, embeds=[], content="> Message timed out. Please run the command again.")
