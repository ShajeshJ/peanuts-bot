import os
import logging
from dotenv import load_dotenv


def get_log_handler() -> logging.Handler:
    """
    Returns a handler that colours the logging output based
    on severity
    """

    class ColourHandler(logging.StreamHandler):
        _colour_map = {
            logging.DEBUG: "\033[30m",
            logging.INFO: "\033[34m",
            logging.WARNING: "\033[33m",
            logging.ERROR: "\033[31m",
            logging.CRITICAL: "\033[91m",
        }

        def __init__(self):
            super().__init__()

        def format(self, record: logging.LogRecord) -> str:
            colour = self._colour_map.get(record.levelno, "\033[0m")
            return f"{colour}{super().format(record)}\033[0m"

    return ColourHandler()


def configure_logging():
    """Configures logging"""

    logging.basicConfig(
        force=True,
        level=os.environ.get("LOG_LEVEL", "INFO"),
        handlers=[get_log_handler()],
    )


def load_env() -> str:
    """Loads environment variables from file, if available"""
    load_dotenv(".env", verbose=True)
    return os.environ["ENV"]


def main():
    """
    Entrypoint of the app
    """
    # configure minimal logs at the top to capture preliminary configuration logs
    logging.basicConfig(level=logging.INFO)

    load_env()
    configure_logging()

    from peanuts_bot import bot

    bot.start()


if __name__ == "__main__":
    main()
