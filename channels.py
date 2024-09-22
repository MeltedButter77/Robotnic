import sqlite3
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
sql_cursor.execute("CREATE TABLE IF NOT EXISTS temp_channels (guild_id INTEGER, channel_id INTEGER, number INTEGER)")
sql_cursor.execute("CREATE TABLE IF NOT EXISTS temp_channel_hubs (guild_id INTEGER, channel_id INTEGER)")
sql_connection.commit()

class CreatorSelectView(View):
    def __init__(self, channels):
        super().__init__()
        self.add_item(CreatorSelectMenu(channels))

class CreatorSelectMenu(Select):
    def __init__(self, channels):

        options = []
        for i, channel in enumerate(channels):
            options.append(discord.SelectOption(label=f"#{channel.name} ({channel.id})", value=channel.id, emoji="🔧"))

        super().__init__(placeholder="Choose a channel creator", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"You selected: {self.values[0]}", ephemeral=True)


class Channels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command()
    async def setup_channel_creator(self, interaction: discord.Interaction):

        query = 'SELECT channel_id FROM temp_channel_hubs WHERE guild_id = ?'
        sql_cursor.execute(query, (interaction.guild.id,))
        rows = sql_cursor.fetchall()

        channels = []
        for row in rows:
            channels.append(self.bot.get_channel(row[0]))
        print(channels)

        # Creating an embed
        embed = discord.Embed(title="Channel Hub Setup", description="Choose an option to set the channel hub.", color=0x00ff00)
        embed.add_field(name="Options", value="You can choose one of the options from the dropdown below.", inline=False)

        # Sending a message with the dropdown menu and embed
        view = CreatorSelectView(channels)  # This creates the view with the dropdown
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.app_commands.command()
    async def set_channel_hub(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        query = 'SELECT channel_id FROM temp_channel_hubs WHERE guild_id = ?'
        sql_cursor.execute(query, (interaction.guild.id,))
        channel_hub_ids = [row[0] for row in sql_cursor.fetchall()]

        if channel.id in channel_hub_ids:
            return await interaction.response.send_message(f"<#{channel.id}> is already a Hub", ephemeral=True)

        query = 'INSERT INTO temp_channel_hubs (guild_id, channel_id, number) VALUES (?, ?, ?)'
        sql_cursor.execute(query, (interaction.guild.id, channel.id, 1))
        sql_connection.commit()
        await interaction.response.send_message(f"Made <#{channel.id}> a channel creator", ephemeral=True)

    @discord.app_commands.command()
    async def remove_channel_hub(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        # This command should be useless with the addition of removing from database when deleted
        query = 'DELETE FROM temp_channel_hubs WHERE guild_id = ? AND channel_id = ?'
        sql_cursor.execute(query, (interaction.guild.id, channel.id,))
        deleted_rows = sql_cursor.rowcount
        sql_connection.commit()
        if deleted_rows > 0:
            await interaction.response.send_message(f"Removed <#{channel.id}> as a channel creator", ephemeral=True)
        else:
            await interaction.response.send_message(f"<#{channel.id}> is not a channel creator", ephemeral=True)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        query = 'DELETE FROM temp_channel_hubs WHERE guild_id = ? AND channel_id = ?'
        sql_cursor.execute(query, (channel.guild.id, channel.id,))
        deleted_rows = sql_cursor.rowcount
        sql_connection.commit()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if after.channel:
            sql_cursor.execute('SELECT channel_id FROM temp_channel_hubs WHERE guild_id = ?', (member.guild.id,))
            channel_hub_ids = [row[0] for row in sql_cursor.fetchall()]

            # Creates Temp Channel
            if after.channel.id in channel_hub_ids:
                # Fetch all temporary channels from the database for this guild
                sql_cursor.execute('SELECT number FROM temp_channels WHERE guild_id = ?', (member.guild.id,))
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
                sql_cursor.execute('INSERT INTO temp_channels (guild_id, channel_id, number) VALUES (?, ?, ?)',
                                   (member.guild.id, channel.id, channel_number))
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

