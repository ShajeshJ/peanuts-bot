import logging
from typing import NamedTuple
import interactions as ipy

from config import CONFIG

logger = logging.getLogger(__name__)


class LoadableExtensions(NamedTuple):
    ext_name: str
    module_path: str

    def to_slash_command_choice(self) -> ipy.SlashCommandChoice:
        return ipy.SlashCommandChoice(name=self.ext_name, value=self.module_path)


ALL_EXTENSIONS: list[LoadableExtensions] = [
    LoadableExtensions("Role Commands", "peanuts_bot.extensions.roles"),
    LoadableExtensions("Channel Commands", "peanuts_bot.extensions.channels"),
    LoadableExtensions("Emoji Commands", "peanuts_bot.extensions.emojis"),
    LoadableExtensions("RNG Commands", "peanuts_bot.extensions.rng"),
    LoadableExtensions("User Commands", "peanuts_bot.extensions.users"),
    LoadableExtensions("Message Commands", "peanuts_bot.extensions.messages"),
]

if CONFIG.IS_LOCAL:
    logger.debug("loading local commands")
    ALL_EXTENSIONS.append(
        LoadableExtensions("Local Commands", "peanuts_bot.extensions.local")
    )
