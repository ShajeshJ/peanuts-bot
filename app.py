import os
import logging
from dotenv import load_dotenv


def init_app_dependencies():
    """
    Run any initializer code that's required for the
    core app to boot up correctly
    """

    env = os.environ.setdefault("ENV", "local")
    if env == "local":
        load_dotenv(".env")

    logging.basicConfig(force=True, level=os.environ.get("LOG_LEVEL", "INFO"))


def main():
    """
    Entrypoint of the app
    """
    init_app_dependencies()

    from peanuts_bot import bot

    bot.start()


if __name__ == "__main__":
    main()
