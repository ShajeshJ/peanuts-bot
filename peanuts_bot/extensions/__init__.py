import logging
from typing import NamedTuple
import interactions as ipy

from config import CONFIG
from peanuts_bot.libraries.stocks_api import is_stocks_api_connected

logger = logging.getLogger(__name__)


class LoadableExtensions(NamedTuple):
    ext_name: str
    module_path: str

    def to_slash_command_choice(self) -> ipy.SlashCommandChoice:
        return ipy.SlashCommandChoice(name=self.ext_name, value=self.module_path)


ALL_EXTENSIONS: list[LoadableExtensions] = [
    LoadableExtensions("Help", "peanuts_bot.extensions.help"),
    LoadableExtensions("Role", "peanuts_bot.extensions.roles"),
    LoadableExtensions("Channel", "peanuts_bot.extensions.channels"),
    LoadableExtensions("Emoji", "peanuts_bot.extensions.emojis"),
    LoadableExtensions("RNG", "peanuts_bot.extensions.rng"),
    LoadableExtensions("User", "peanuts_bot.extensions.users"),
    LoadableExtensions("Message", "peanuts_bot.extensions.messages"),
]

if is_stocks_api_connected():
    ALL_EXTENSIONS.append(LoadableExtensions("Stock", "peanuts_bot.extensions.stocks"))
else:
    logger.warning("stocks api is not connected, skipping stocks commands")

if CONFIG.IS_LOCAL:
    logger.debug("loading local commands")
    ALL_EXTENSIONS.append(LoadableExtensions("Local", "peanuts_bot.extensions.local"))
