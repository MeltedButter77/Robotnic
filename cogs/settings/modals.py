import discord
from discord.ui import View, Select, Button, Modal, InputText


def english_list(items):
    items = [f"`{str(i).capitalize()}`" for i in items]
    if not items:
        return "None"
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


class SettingsModal(discord.ui.DesignerModal):
    def __init__(self, bot, ctx):
        super().__init__(title="Edit Server Settings")
        self.bot = bot
        guild_settings = self.bot.repos.guild_settings.get(ctx.guild.id)

        self._add_enabled_controls(guild_settings)
        self._add_mention_owner(guild_settings)
        self._add_control_options(guild_settings)

    def _add_enabled_controls(self, guild_settings):
        enabled_controls = guild_settings["enabled_controls"]
        controls_options = [
            discord.SelectOption(value="rename", label="Rename Channel", emoji="🏷️", default="rename" in enabled_controls),
            discord.SelectOption(value="limit", label="Edit User Limit", emoji="🚧", default="limit" in enabled_controls),
            discord.SelectOption(value="clear", label="Clear Messages", emoji="🧽", default="clear" in enabled_controls),
            discord.SelectOption(value="ban", label="Ban Users or Roles", emoji="🔨", default="ban" in enabled_controls),
            discord.SelectOption(value="give", label="Give Ownership", emoji="🎁", default="give" in enabled_controls),
            discord.SelectOption(value="delete", label="Delete Channel", emoji="🗑️", default="delete" in enabled_controls),
            discord.SelectOption(value="lock", label="Lock Channel", emoji="🔒", default="lock" in enabled_controls),
            discord.SelectOption(value="hide", label="Hide Channel", emoji="🙈", default="hide" in enabled_controls),
        ]
        controls_select = Select(placeholder="Select options to Enable or Disable", options=controls_options, max_values=len(controls_options), min_values=0, required=False)
        self.controls_select_label = discord.ui.Label(
            "Enable channel controls available to users.",
            controls_select,
        )
        self.add_item(self.controls_select_label)

    def _save_enabled_controls(self, guild_id, embed):
        enabled_controls = self.controls_select_label.item.values
        self.bot.repos.guild_settings.edit(guild_id, enabled_controls=list(enabled_controls))
        embed.add_field(name=f"Enabled Control Options", value=f"{english_list(enabled_controls)}", inline=False)

    def _add_mention_owner(self, guild_settings):
        mention_owner = guild_settings["mention_owner_bool"]
        options = [
            discord.SelectOption(value="true", label="Do Mention", default=mention_owner),
            discord.SelectOption(value="false", label="Do Not Mention", default=not mention_owner),
        ]

        self.mention_owner_label = discord.ui.Label(
            "Mention owner upon creation?",
            discord.ui.Select(
                options=options,
                min_values=1,
                max_values=1,
                required=True
            ),
        )
        self.add_item(self.mention_owner_label)

    def _save_mention_owner(self, guild_id, embed):
        should_mention = self.mention_owner_label.item.values[0]
        if should_mention == "false":
            should_mention = False
        self.bot.repos.guild_settings.edit(guild_id, mention_owner=should_mention)
        embed.add_field(name=f"Mention Owner", value=f"`{should_mention}`", inline=False)

    def _add_control_options(self, guild_settings):
        enabled_options = guild_settings["control_options"]
        default = "Dropdown Menu"
        if "dropdown" in enabled_options:
            default = "Dropdown Menu"
        elif "buttons" in enabled_options and "labels" in enabled_options:
            default = "Buttons (Icons & Labels)"
        elif "buttons" in enabled_options:
            default = "Buttons (Icons Only)"
        control_options = [
            discord.SelectOption(label="Dropdown Menu", default=default == "Dropdown Menu"),
            discord.SelectOption(label="Buttons (Icons & Labels)", default=default == "Buttons (Icons & Labels)"),
            discord.SelectOption(label="Buttons (Icons Only)", default=default == "Buttons (Icons Only)"),
        ]
        options_select = Select(placeholder="Select an option", options=control_options, max_values=1, min_values=1, required=True)
        self.options_select_label = discord.ui.Label(
            "Select how to control your channels",
            options_select,
        )
        self.add_item(self.options_select_label)

    def _save_control_options(self, guild_id, embed):
        control_type = self.options_select_label.item.values[0]
        selected_control_options = []

        # Control type
        control_type_map = {
            "Dropdown Menu": {"dropdown", "labels"},
            "Buttons (Icons & Labels)": {"buttons", "icons", "labels"},
            "Buttons (Icons Only)": {"buttons", "icons"},
        }
        selected_control_options.extend(control_type_map.get(control_type, []))

        self.bot.repos.guild_settings.edit(guild_id, control_options=selected_control_options)
        embed.add_field(name=f"Control Type", value=f"`{control_type}`", inline=False)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Submitted!",
            description=f"",
            color=discord.Color.green()
        )
        embed.set_footer(text="This message will disappear in 60 seconds.")

        self._save_enabled_controls(interaction.guild_id, embed)
        self._save_mention_owner(interaction.guild_id, embed)
        self._save_control_options(interaction.guild_id, embed)

        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=60)


class LogsModal(discord.ui.DesignerModal):
    def __init__(self, bot, ctx):
        super().__init__(title="Edit Server Settings")
        self.bot = bot
        guild_settings = self.bot.repos.guild_settings.get(ctx.guild.id)

        self._add_log_channel(guild_settings)
        self._add_log_events(guild_settings)

    def _add_log_channel(self, guild_settings):
        if guild_settings["logs_channel_id"] is not None and int(guild_settings["logs_channel_id"]) != 0:
            log_channel = self.bot.get_channel(guild_settings["logs_channel_id"])
        else:
            log_channel = None

        self.log_channel_select = discord.ui.Label(
            "Select a Log Channel",
            discord.ui.ChannelSelect(
                channel_types=[discord.ChannelType.text],
                min_values=1,
                max_values=1,
                default_values=[log_channel] if log_channel else None,
                required=False
            ),
        )
        self.add_item(self.log_channel_select)

    def _save_log_channel(self, guild_id, embed):
        if len(self.log_channel_select.item.values) >= 1:
            log_channel = self.log_channel_select.item.values[0]
            self.bot.repos.guild_settings.edit(guild_id, logs_channel_id=log_channel.id)
            embed.add_field(name=f"Selected Log Channel", value=f"{log_channel.mention}/`#{log_channel.name}` (`{log_channel.id}`)", inline=False)
        else:
            self.bot.repos.guild_settings.edit(guild_id, logs_channel_id=0)
            embed.add_field(name=f"Selected Log Channel", value=f"None/Disabled", inline=False)

    def _add_log_events(self, guild_settings):
        enabled_events = guild_settings["enabled_log_events"]
        events_options = [
            discord.SelectOption(value="channel_create", label="channel_create", emoji="🎁", default="channel_create" in enabled_events),
            discord.SelectOption(value="channel_rename", label="channel_rename", emoji="🏷️", default="channel_rename" in enabled_events),
            discord.SelectOption(value="channel_remove", label="channel_remove", emoji="🗑️", default="channel_remove" in enabled_events),
            discord.SelectOption(value="profanity_block", label="profanity_block", emoji="😶", default="profanity_block" in enabled_events),
        ]
        events_select = Select(placeholder="Select options to Enable or Disable", options=events_options, max_values=len(events_options), min_values=0, required=False)

        self.events_select_label = discord.ui.Label(
            "Select which Events to Log",
            events_select,
        )
        self.add_item(self.events_select_label)

    def _save_log_events(self, guild_id, embed):
        enabled_log_events = self.events_select_label.item.values
        self.bot.repos.guild_settings.edit(guild_id, enabled_log_events=enabled_log_events)
        embed.add_field(name=f"Enabled Log Events", value=f"{english_list(enabled_log_events)}", inline=False)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Submitted!",
            description=f"",
            color=discord.Color.green()
        )
        embed.set_footer(text="This message will disappear in 60 seconds.")

        self._save_log_channel(interaction.guild_id, embed)
        self._save_log_events(interaction.guild_id, embed)

        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=60)
