from database.creator_channels_repo import CreatorChannelsRepository
from database.guild_settings_repo import GuildSettingsRepository
from database.temp_channels_repo import TempChannelsRepository


class Repositories:
    def __init__(self, database):
        self.guild_settings = GuildSettingsRepository(database, repos=self)
        self.creator_channels = CreatorChannelsRepository(database, repos=self)
        self.temp_channels = TempChannelsRepository(database, repos=self)
