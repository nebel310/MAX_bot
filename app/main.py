import os
import logging
from pathlib import Path
import aiomax

try:
    # Preferred relative import when package context is known (python -m app.main)
    from .handlers import setup_handlers  # type: ignore
except ImportError:
    # Fallback for direct script execution (python app/main.py)
    from app.handlers import setup_handlers  # type: ignore


def _load_env_from_file() -> None:
    """Minimal .env loader (no external deps).

    Loads key=value pairs from .env next to this file into os.environ
    if the key is not already defined. Ignores empty lines and lines
    starting with '#'. Only the first '=' splits key and value.
    """
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception as e:
        logging.warning("Failed to load .env: %s", e)


def create_bot() -> aiomax.Bot:
    """Create and configure bot instance using BOT_TOKEN from .env only."""
    _load_env_from_file()
    token = os.getenv("BOT_TOKEN")
    if not token or not token.strip():
        raise RuntimeError("BOT_TOKEN must be set in app/.env (key BOT_TOKEN=...)")
    return aiomax.Bot(token, default_format="markdown")


def bootstrap() -> aiomax.Bot:
    bot = create_bot()
    setup_handlers(bot)
    return bot


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot_instance = bootstrap()
    bot_instance.run()
