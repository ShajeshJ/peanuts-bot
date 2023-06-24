import logging
from typing import NamedTuple
import interactions as ipy

from peanuts_bot.config import CONFIG

logger = logging.getLogger(__name__)


class ExtInfo(NamedTuple):
    ext_name: str
    module_path: str

    def to_slash_command_choice(self) -> ipy.SlashCommandChoice:
        return ipy.SlashCommandChoice(name=self.ext_name, value=self.module_path)


ALL_EXTENSIONS: list[ExtInfo] = [
    ExtInfo("Help", "peanuts_bot.extensions.help"),
    ExtInfo("Role", "peanuts_bot.extensions.roles"),
    ExtInfo("Channel", "peanuts_bot.extensions.channels"),
    ExtInfo("Emoji", "peanuts_bot.extensions.emojis"),
    ExtInfo("RNG", "peanuts_bot.extensions.rng"),
    ExtInfo("User", "peanuts_bot.extensions.users"),
    ExtInfo("Message", "peanuts_bot.extensions.messages"),
]

if CONFIG.IS_ALPHAV_CONNECTED:
    ALL_EXTENSIONS.append(ExtInfo("Stock", "peanuts_bot.extensions.stocks"))
else:
    logger.warning("stocks api is not connected, skipping stocks commands")

if CONFIG.IS_LOCAL:
    logger.debug("loading local commands")
    ALL_EXTENSIONS.append(ExtInfo("Local", "peanuts_bot.extensions.local"))
