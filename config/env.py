import os
import sys
import dotenv
from config.paths import ENV_PATH


def load_tokens(logger) -> tuple[str, str | None]:
    # Check if .env exists, if not create a new one
    placeholder = "TOKEN_HERE"
    if not os.path.exists(ENV_PATH):
        with open(ENV_PATH, 'w') as f:
            f.write(f"TOKEN={placeholder}\n")
        logger.error(
            "No .env file found, one has been created. "
            "Please replace 'TOKEN_HERE' with your actual bot token."
        )
        sys.exit(1)
    else:
        logger.debug(
            "Valid .env file found. "
        )

    # Get Token
    dotenv.load_dotenv()
    bot_token = os.getenv("TOKEN")
    topgg_token = os.getenv("TOPGG_TOKEN")
    # Handle placeholder or no token
    if bot_token == placeholder or not bot_token:
        logger.error(
            "No valid TOKEN found in .env. "
            "Please replace 'TOKEN_HERE' with your actual bot token."
        )
        sys.exit(1)
    else:
        logger.debug(
            "Token found. "
        )

    return bot_token, topgg_token
