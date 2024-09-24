import sqlite3
from typing import List
import discord
from discord.ext import commands
from discord.ui import Select, View
import json

# Load the token from config.json
with open('config.json') as config_file:
    config = json.load(config_file)

# Connect to SQLite database and create a table if it doesn't exist
sql_connection = sqlite3.connect('my_database.db')
sql_cursor = sql_connection.cursor()
sql_cursor.execute("CREATE TABLE IF NOT EXISTS temp_channels (guild_id INTEGER, channel_id INTEGER, creator_id INTEGER, number INTEGER)")
sql_cursor.execute("CREATE TABLE IF NOT EXISTS temp_channel_hubs (guild_id INTEGER, channel_id INTEGER)")
sql_connection.commit()

# Creator Edit/Selection View (like an interaction menu with multiple buttons and stuff)
class CreatorSelectView(View):
    def __init__(self,
                menu_channels: List[discord.TextChannel] = None,
                create_button: bool = False,
                donate_button: bool = False,
                back_button: bool = False,
            ):
        super().__init__()
        if menu_channels:
            self.add_item(CreatorSelectMenu(menu_channels))
        if create_button:
            self.add_item(discord.ui.Button(label="Create new Creator", style=discord.ButtonStyle.success, custom_id="create_channel_creator"))
        if donate_button:
            self.add_item(discord.ui.Button(label="Support", url=f"{config['support_server']}", style=discord.ButtonStyle.link))
        if back_button:
            self.add_item(discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, custom_id="back_creator_menu"))


# Creator menu selector panel
class CreatorSelectMenu(Select):
    def __init__(self, channels):
        options = []
        for i, channel in enumerate(channels):
            options.append(discord.SelectOption(label=f"#{channel.name} ({channel.id})", value=channel.id, emoji="🔧"))

        if len(options) < 1:
            options.append(discord.SelectOption(label=f"None", value="None", emoji="🔧"))
            super().__init__(placeholder="No creators to select", custom_id="channel_creator_select", options=options, disabled=True, min_values=1, max_values=1)
        else:
            super().__init__(placeholder="Select a creator to edit", custom_id="channel_creator_select", options=options, min_values=1, max_values=1)


class Channels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        # Check if the interaction is from a component with a specific custom_id
        if interaction.data.get("custom_id") == "channel_creator_select":
            selected_channel = discord.utils.get(interaction.guild.voice_channels, id=int(interaction.data.get("values")[0]))

            # Creating an embed
            embed = discord.Embed(title=f"#{selected_channel.name}", description="This channel is cool", color=0x00ff00)
            embed.add_field(name="Name", value=f"{selected_channel.name}", inline=True)
            embed.add_field(name="ID", value=f"{selected_channel.id}", inline=True)
            embed.add_field(name="Category", value=f"<#{selected_channel.category_id}>" if selected_channel.category_id else "None", inline=True)

            # Update the menu in the message
            query = 'SELECT channel_id FROM temp_channel_hubs WHERE guild_id = ?'
            sql_cursor.execute(query, (interaction.guild.id,))
            rows = sql_cursor.fetchall()
            channels = []
            for row in rows:
                channels.append(self.bot.get_channel(row[0]))
            view = CreatorSelectView(menu_channels=channels, back_button=True)
            await interaction.response.edit_message(embed=embed, view=view)

        if interaction.data.get("custom_id") == "back_creator_menu":
            # Create menu with channel hubs
            query = 'SELECT channel_id FROM temp_channel_hubs WHERE guild_id = ?'
            sql_cursor.execute(query, (interaction.guild.id,))
            rows = sql_cursor.fetchall()
            channels = []
            for row in rows:
                channels.append(self.bot.get_channel(row[0]))
            view = CreatorSelectView(channels, create_button=True)

            # Creating an embed
            embed = discord.Embed(title="Channel Hub Setup", description="Choose an option to set the channel hub.", color=0x00ff00)
            embed.add_field(name="Options", value="You can choose one of the options from the dropdown below.", inline=False)

            # Sending a message with the dropdown menu and embed
            await interaction.response.edit_message(embed=embed, view=view)

        if interaction.data.get("custom_id") == "create_channel_creator":
            # Create channel and add to db
            channel = await interaction.guild.create_voice_channel(name="➕ Create Channel",)
            query = 'INSERT INTO temp_channel_hubs (guild_id, channel_id) VALUES (?, ?)'
            sql_cursor.execute(query, (interaction.guild.id, channel.id))
            sql_connection.commit()

            # Update the menu in the message
            query = 'SELECT channel_id FROM temp_channel_hubs WHERE guild_id = ?'
            sql_cursor.execute(query, (interaction.guild.id,))
            rows = sql_cursor.fetchall()
            channels = []
            for row in rows:
                channels.append(self.bot.get_channel(row[0]))
            view = CreatorSelectView(menu_channels=channels, create_button=True, donate_button=True)
            await interaction.response.edit_message(view=view)

            await interaction.followup.send(f"Created <#{channel.id}>.", ephemeral=True)

    @discord.app_commands.command()
    async def setup_creators(self, interaction: discord.Interaction):
        # Create menu with channel hubs
        query = 'SELECT channel_id FROM temp_channel_hubs WHERE guild_id = ?'
        sql_cursor.execute(query, (interaction.guild.id,))
        rows = sql_cursor.fetchall()
        channels = []
        for row in rows:
            channels.append(self.bot.get_channel(row[0]))
        view = CreatorSelectView(menu_channels=channels, create_button=True, donate_button=True)

        # Creating an embed
        embed = discord.Embed(title="Channel Hub Setup", description="Choose an option to set the channel hub.", color=0x00ff00)
        embed.add_field(name="Options", value="You can choose one of the options from the dropdown below.", inline=False)

        # Sending a message with the dropdown menu and embed
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        query = 'DELETE FROM temp_channel_hubs WHERE guild_id = ? AND channel_id = ?'
        sql_cursor.execute(query, (channel.guild.id, channel.id,))
        sql_connection.commit()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if after.channel:
            query = 'SELECT channel_id FROM temp_channel_hubs WHERE guild_id = ?'
            sql_cursor.execute(query, (member.guild.id,))
            channel_hub_ids = [row[0] for row in sql_cursor.fetchall()]

            # Creates Temp Channel
            if after.channel.id in channel_hub_ids:
                # Fetch all temporary channels from the database for this guild
                query = 'SELECT number FROM temp_channels WHERE guild_id = ? AND creator_id = ?'
                sql_cursor.execute(query, (member.guild.id, after.channel.id))
                values = [row[0] for row in sql_cursor.fetchall()]

                # Find the lowest available number for the new channel
                channel_number = 1
                for i, value in enumerate(sorted(values)):
                    if not value == i + 1:
                        channel_number = i + 1
                        break
                    channel_number = value + 1

                # Create the voice channel
                channel = await member.guild.create_voice_channel(
                    name="Lobby " + f"{channel_number}",
                    category=after.channel.category
                )

                # Insert the new temporary channel into the database
                sql_cursor.execute('INSERT INTO temp_channels (guild_id, channel_id, creator_id, number) VALUES (?, ?, ?, ?)',
                                   (member.guild.id, channel.id, after.channel.id, channel_number))
                sql_connection.commit()

                # Move the member to the newly created channel
                await member.move_to(channel)

        # Deletes Temp Channel
        if before.channel:
            # Check if the member has left a temp channel and if that channel is empty
            sql_cursor.execute('SELECT * FROM temp_channels WHERE channel_id = ?', (before.channel.id,))
            result = sql_cursor.fetchone()

            if result and len(before.channel.members) == 0:
                # Delete the temp channel from the server
                left_channel = discord.utils.get(member.guild.voice_channels, id=before.channel.id)
                if left_channel:
                    await left_channel.delete()

                # Remove the channel from the database
                sql_cursor.execute('DELETE FROM temp_channels WHERE channel_id = ?', (before.channel.id,))
                sql_connection.commit()


async def setup(bot):
    await bot.add_cog(Channels(bot))

