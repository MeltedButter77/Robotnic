import discord
from discord.ui import View, Select, Button, Modal, InputText


class TestModal(discord.ui.DesignerModal):
    def __init__(self):
        super().__init__(title="Edit Your Channel")

        # Define the text inputs
        # self.channel_name = discord.ui.InputText(
        #     label="Channel Name (Blank = Default)",
        #     placeholder=f"sdas",
        #     required=False,
        #     max_length=25
        # )

        self.option_select = discord.ui.Label(
            "Test Select",
            discord.ui.Select(
                options=[
                    discord.SelectOption(label="1"),
                    discord.SelectOption(label="2"),
                    discord.SelectOption(label="3")
                ],
            ),
        )
        self.add_item(self.option_select)

        # Integer input (short text input; cast to int on submit)
        self.int_input = discord.ui.Label(
            "Enter an Integer",
            discord.ui.TextInput(
                placeholder="Type a number...",
                required=True,
                max_length=10,
            ),
        )
        self.add_item(self.int_input)

        # Text input (longer text field)
        self.text_input = discord.ui.Label(
            "Enter Text",
            discord.ui.TextInput(
                placeholder="Type any text here...",
                required=False,
                max_length=500,
            ),
        )
        self.add_item(self.text_input)

        # Category select
        self.category_select = discord.ui.Label(
            "Select a Category",
            discord.ui.ChannelSelect(
                channel_types=[discord.ChannelType.category],
                min_values=1,
                max_values=1,
                placeholder="Default: Same as Creator"
            ),
        )
        self.add_item(self.category_select)

    async def callback(self, interaction: discord.Interaction):
        # Update the channel
        option_select = str(self.option_select.item.value)
        int_value = int(self.int_input.item.value)
        text_value = self.text_input.item.value
        category = self.category_select.item.value

        embed = discord.Embed(
            title="Submitted",
            description=f"{option_select}, {int_value}, {text_value}, {category}",
            color=discord.Color.blue()
        )
        embed.set_footer(text="This message will disappear in 30 seconds.")
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=30)


class EditModal(discord.ui.DesignerModal):
    def __init__(self, view, creator_id):
        super().__init__(title="Example Modal")
        self.view = view
        self.creator_id = creator_id
        creator_info = self.view.bot.repos.creator_channels.get_info(self.creator_id)

        self.child_name_label = discord.ui.Label(
            "Child Name, use: {user} {activity} {count}",
            discord.ui.TextInput(
                placeholder=f"{creator_info.child_name}",
                required=False,
                max_length=100,
            ),
        )
        self.add_item(self.child_name_label)

        self.user_limit_label = discord.ui.Label(
            "User Limit (0 = Unlimited)",
            discord.ui.TextInput(
                placeholder=f"{creator_info.user_limit}",
                required=False,
                max_length=500,
            ),
        )
        self.add_item(self.user_limit_label)

        self.child_overwrites_label = discord.ui.Label(
            "Permission Handling",
            discord.ui.Select(
                options=[
                    discord.SelectOption(value="1", label="Copy Creator Channel", default=True if creator_info.child_overwrites == 1 else False),
                    discord.SelectOption(value="2", label="Copy Child's Category", default=True if creator_info.child_overwrites == 2 else False),
                    discord.SelectOption(value="0", label="No Permissions", default=True if creator_info.child_overwrites == 0 else False),
                ],
                min_values=1,
                max_values=1,
                required=True
            ),
        )
        self.add_item(self.child_overwrites_label)

        category = self.view.bot.get_channel(creator_info.child_category_id)
        self.category_label = discord.ui.Label(
            "Optional: Set a Category",
            discord.ui.ChannelSelect(
                channel_types=[discord.ChannelType.category],
                min_values=1,
                max_values=1,
                required=False,
                default_values=[category] if category else None,
                placeholder="Default: Same as Creator"
            ),
        )
        self.add_item(self.category_label)

    async def callback(self, interaction: discord.Interaction):
        errors = []

        child_name = self.child_name_label.item.value
        user_limit = self.user_limit_label.item.value
        child_overwrites = self.child_overwrites_label.item.values[0] if len(self.child_overwrites_label.item.values) > 0 else None
        child_category_id = self.category_label.item.values[0].id if len(self.category_label.item.values) > 0 else None

        creator_info = self.view.bot.repos.creator_channels.get_info(self.creator_id)
        if child_name:
            # Validate Child name length
            child_name = child_name.strip()
            if len(child_name) > 100:
                errors.append("Child name must be under 100 characters.")
        else:
            child_name = creator_info.child_name

        if user_limit:
            try:
                user_limit = int(user_limit)
                if not (0 <= user_limit <= 99):
                    errors.append("User limit must be an integer between `0` and `99` inclusive.")
            except ValueError:
                errors.append("User limit must be an integer.")
        else:
            user_limit = creator_info.user_limit

        if errors:
            await interaction.response.send_message(
                f"Invalid input:\n" + "\n".join(f"- {error}" for error in errors),
                ephemeral=True
            )
            await self.view.update()
            return

        self.view.bot.repos.creator_channels.edit(
            channel_id=self.creator_id,
            child_name=child_name,
            user_limit=user_limit,
            child_category_id=child_category_id,
            child_overwrites=child_overwrites
        )

        embed = discord.Embed(
            title="Updated!",
            description=f"",
            color=discord.Color.green()
        )
        embed.set_footer(text="This message will disappear in 10 seconds.")
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)
        await self.view.update()
