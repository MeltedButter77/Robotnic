import discord
from discord.ui import View, Select, Button, Modal, InputText


class EditModal(Modal):
    def __init__(self, view, creator_id, is_advanced: bool = False):
        super().__init__(title="Example Modal")
        self.view = view
        self.creator_id = creator_id

        # Add input fields
        self.add_item(InputText(label="Name of Temporary Channel Created", placeholder="Can include variables {user}, {activity} or {count}", required=False))
        if is_advanced:
            self.add_item(InputText(label="User Limit", placeholder="Enter integer 0-99 (0 = Unlimited)", required=False))
            self.add_item(InputText(label="Temp Channel Category ID", placeholder="Enter 0 (for same as creator) or category ID", required=False))
            self.add_item(InputText(label="Temp Channel Permissions", placeholder="Enter integer 0-2 (differences explained in /creator menu)", required=False))

    async def callback(self, interaction: discord.Interaction):
        errors = []

        db_creator_channel_info = self.view.bot.db.get_creator_channel_info(self.creator_id)

        # Validate Child name length
        child_name = self.children[0].value.strip() or db_creator_channel_info.child_name
        if len(child_name) > 100:
            errors.append("Child name must be under 100 characters.")

        # Validate user limit
        # Each input may not exist as the simple version will only have 1 item in list self.children
        user_limit_raw = self.children[1].value.strip() if len(self.children) > 1 else ""

        if user_limit_raw == "":
            user_limit = db_creator_channel_info.user_limit
        else:
            try:
                user_limit = int(user_limit_raw)
                if not (0 <= user_limit <= 99):
                    errors.append("User limit must be an integer between `0` and `99` inclusive.")
            except ValueError:
                errors.append("User limit must be an integer.")

        # Validate Child Category ID
        category_raw = self.children[2].value.strip() if len(self.children) > 1 else ""
        if category_raw == "":
            child_category_id = db_creator_channel_info.child_category_id
        else:
            try:
                child_category_id = int(category_raw)
                category = self.view.bot.get_channel(child_category_id)
                if child_category_id < 0 or category is None:
                    errors.append("Category ID must be `0` or a valid category ID (positive integer).")
            except ValueError:
                errors.append("Category ID must be an integer.")

        # Validate Child Overwrite optiuons
        overwrites_raw = self.children[3].value.strip() if len(self.children) > 1 else ""
        if overwrites_raw == "":
            child_overwrites = db_creator_channel_info.child_overwrites
        else:
            try:
                child_overwrites = int(overwrites_raw)
                if child_overwrites not in (0, 1, 2):
                    errors.append("Permissions must be `0` (None), `1` (From Creator), or `2` (From Category).")
            except ValueError:
                errors.append("Permissions must be an integer `0` (None), `1` (From Creator), or `2` (From Category).")

        # --- Handle Errors ---
        if errors:
            await interaction.response.send_message(
                f"Invalid input:\n" + "\n".join(f"- {error}" for error in errors),
                ephemeral=True
            )
            await self.view.update()
            return

        self.view.bot.db.edit_creator_channel(
            channel_id=self.creator_id,
            child_name=child_name,
            user_limit=user_limit,
            child_category_id=child_category_id,
            child_overwrites=child_overwrites
        )

        await interaction.response.send_message(
            f"Creator channel updated!",
            ephemeral=True
        )
        await self.view.update()
