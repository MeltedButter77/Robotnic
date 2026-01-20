from database.database import Database
from bot.bot import Bot
from config.bot_settings import load_settings
from bot.logging import setup_program_loggers
from config.env import load_tokens

settings = load_settings()
logger = setup_program_loggers(settings)
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
