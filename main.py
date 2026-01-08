from database.database import Database
from bot.bot import Bot
from config.bot_settings import load_settings
from config.logging import setup_logging
from config.env import load_tokens

settings = load_settings()
logger = setup_logging(settings)
bot_token, topgg_token = load_tokens(logger)
database = Database()

bot = Bot(
    token=bot_token,
    topgg_token=topgg_token,
    logger=logger,
    database=database,
    settings=settings,
)

bot.run()
