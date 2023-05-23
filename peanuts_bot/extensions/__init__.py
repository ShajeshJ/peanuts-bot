import logging
import interactions as ipy

from config import CONFIG

logger = logging.getLogger(__name__)

ALL_EXTENSIONS: list[ipy.SlashCommandChoice] = [
    # ipy.SlashCommandChoice(name="Role Commands", value="peanuts_bot.extensions.roles"),
    # ipy.SlashCommandChoice(
    #     name="Channel Commands", value="peanuts_bot.extensions.channels"
    # ),
    # ipy.SlashCommandChoice(
    #     name="Emoji Commands", value="peanuts_bot.extensions.emojis"
    # ),
    # ipy.SlashCommandChoice(name="RNG Commands", value="peanuts_bot.extensions.rng"),
    # ipy.SlashCommandChoice(name="User Commands", value="peanuts_bot.extensions.users"),
    # ipy.SlashCommandChoice(
    #     name="Message Commands", value="peanuts_bot.extensions.messages"
    # ),
]

if CONFIG.IS_LOCAL:
    logger.debug("loading local commands")
    ALL_EXTENSIONS.append(
        ipy.SlashCommandChoice(
            name="Local Commands", value="peanuts_bot.extensions.local"
        )
    )
