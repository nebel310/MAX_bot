import os
import logging
import aiomax

from .handlers import *  # python -m app.main


def create_bot() -> aiomax.Bot:
    """Create and configure bot instance.

    Token is currently hard-coded for speed; move to env var ASAP:
      setx BOT_TOKEN "<token>"
    Then replace below with: os.getenv("BOT_TOKEN")
    """
    token = os.getenv("BOT_TOKEN", "f9LHodD0cOJGa6xX_2Y-CwhDklpJyumJdNZwfS9y92qymFwPtTVJRiA0zweaLmACFxCfHn4WG6q-i9dr0Wap")
    return aiomax.Bot(token, default_format="markdown")


def bootstrap() -> aiomax.Bot:
    bot = create_bot()
    setup_handlers(bot)
    return bot


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot_instance = bootstrap()
    bot_instance.run()
