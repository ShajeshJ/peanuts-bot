import os
import logging
from dotenv import load_dotenv

env = os.environ.setdefault("ENV", "local")
if env == "local":
    load_dotenv(".env")

logging.basicConfig(force=True, level=os.environ.get("LOG_LEVEL", "INFO"))

import peanuts_bot
