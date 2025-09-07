import aiohttp
from contextlib import asynccontextmanager
import logging

from peanuts_bot.config import CONFIG


logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_api_session():
    async with aiohttp.ClientSession(
        "https://discord.com/api/v10/",
        headers={"Authorization": f"Bot {CONFIG.BOT_TOKEN}"},
    ) as session:
        yield session


async def get_bot_description() -> str:
    try:
        async with get_api_session() as session:
            async with session.get("applications/@me") as response:
                response.raise_for_status()
                data = await response.json()

        return data.get("description", "")
    except:
        logger.warning("failed to fetch bot description", exc_info=True)
        return ""
