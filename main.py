import os
import sys
import discord
from database import Database
from topgg import DBLClient
import coroutine_tasks
from manage_vcs.renamer import TempChannelRenamer
from config.bot_settings import load_settings
from config.logging import setup_logging
from config.env import load_tokens

# Main.py Logic Structure
# Retrieve Settings.json
# Initialize Discord and Bot loggers
# Retrieve bot token
# Bot class, handles all bot methods
# Initialize Bot object and set a database object as an attribute
# Run bot

settings = load_settings()
logger = setup_logging(settings)
bot_token, topgg_token = load_tokens(logger)


# Subclassed discord.Bot allowing for methods to correspond directly with bot triggers
class Bot(discord.AutoShardedBot):
    def __init__(self, token, topgg_token, logger, database):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.presences = True
        intents.members = True
        super().__init__(intents=intents)
        self.token = token
        self.logger = logger
        self.db = database
        self.renamer = TempChannelRenamer(self)

        self.settings = settings
        self.notification_channel = None

        self.topgg_client = None
        if topgg_token:
            self.topgg_client = DBLClient(self, topgg_token)
            self.logger.info(f'Connected TOPGG Client')

    async def send_bot_log(self, type, message, embeds=None):
        if self.notification_channel and settings["notifications"].get(str(type), False):
            await self.notification_channel.send(message, embeds=embeds)

    async def on_ready(self):
        self.logger.info(f'Logged in as {self.user}')
        await coroutine_tasks.create_tasks(self)

        self.notification_channel = self.get_channel(settings["notifications"].get("channel_id", None))
        await self.send_bot_log(type="start", message=f"Bot {self.user.mention} started.")

        await bot.sync_commands()
        self.logger.info(f'Commands synced')

    async def close(self):
        self.logger.info(f'Logging out {self.user}')

        # Update all control messages with a disabled button saying its expired
        for temp_channel_id in self.db.get_temp_channel_ids():
            temp_channel = self.get_channel(temp_channel_id)
            # Searches first 10 messages for first send by the bot. This will almost always be the creator
            async for control_message in temp_channel.history(limit=10, oldest_first=True):
                if control_message.author.id == bot.user.id:
                    # Create a new view with one disabled button
                    view = discord.ui.View()
                    view.add_item(
                        discord.ui.Button(
                            label="This control message has expired",
                            style=discord.ButtonStyle.secondary,
                            disabled=True
                        )
                    )
                    # Edit the message to show the new view
                    await control_message.edit(view=view)

        await self.send_bot_log(type="stop", message=f"Bot {self.user.mention} stopping.")
        await super().close()

    async def on_guild_join(self, guild):
        # This event is triggered when the bot joins a new guild
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                embed = discord.Embed(
                    title=f"Hello {guild.name}! 🎉",
                    description="Thank you for inviting me to your server! 😊\nHere are the commands to get started.",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="/setup",
                    value="Allows an admin to setup a channel creator (or channel hub) which dynamically creates voice channels when users join them.",
                    inline=False
                )
                embed.add_field(
                    name="/setup_advanced",
                    value="Same as /setup except it allows more customisation. Change name, user limits, category of created channels and the permissions",
                    inline=False
                )
                embed.set_footer(text="Need more help? Reach out to support below!")
                view = discord.ui.View()
                view.add_item(discord.ui.Button(style=discord.ButtonStyle.url,
                                                label="Contact Support",
                                                url=f"https://discord.gg/rcAREJyMV5"))
                # view.add_item(discord.ui.Button(style=discord.ButtonStyle.url,
                #                                 label="Visit Website",
                #                                 url=f"link"))
                await channel.send("Thanks for inviting me!", embed=embed, view=view)
                break

        # Create the embed with the server information
        embed = discord.Embed(
            title="Joined a New Server!",
            description=f"",
            color=discord.Color.green()
        )
        embed.add_field(name="Server Name", value=guild.name, inline=True)
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=f"{guild.owner} (ID: {guild.owner_id})", inline=True)
        embed.add_field(name="Member Count", value=guild.member_count, inline=True)
        embed.add_field(name="Creation Date", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        embed.add_field(name="Region/Locale", value=str(guild.preferred_locale), inline=True)
        await self.send_bot_log(type="guild_join", message=f"", embeds=[embed])

    async def on_application_command_error(self, ctx, exception):
        if isinstance(exception.original, discord.Forbidden):
            await ctx.send("I require more permissions.")
        else:
            self.logger.error(f"ERROR in {__name__}\nContext: {ctx}\nException: {exception}")
            await ctx.send("Error, check logs. Type: on_application_command_error")

    def run(self):
        try:
            super().run(self.token)
        except Exception as e:
            self.logger.error(
                "Could not log in. Invalid TOKEN. "
                "Please replace 'TOKEN_HERE' with your actual bot token."
            )
            sys.exit(1)


bot = Bot(bot_token, topgg_token, logger, Database("database.db"))
# Load all cogs from /cogs
for filename in os.listdir("./cogs"):
    if filename.endswith(".py") and not filename.startswith("_"):
        bot.load_extension(f"cogs.{filename[:-3]}")
        bot.logger.debug(f"Loaded cog: {filename}")


bot.run()
