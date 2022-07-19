from __future__ import annotations

import logging
import os
from dotenv import load_dotenv

if "BOT_TOKEN" not in os.environ:
    load_dotenv(".env")

# Must configure logging ASAP
logging.basicConfig(force=True, level=os.environ.get("LOG_LEVEL", "INFO"))

from config import CONFIG

logging.info(CONFIG.IS_DEBUG)
