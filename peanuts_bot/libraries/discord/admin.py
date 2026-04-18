from enum import Enum
import logging
import traceback

import discord
from discord import app_commands

from peanuts_bot.config import CONFIG
from peanuts_bot.libraries.discord.api import get_bot_description


logger = logging.getLogger(__name__)


async def send_error_to_admin(error: Exception, bot: discord.Client) -> None:
    """Forwards the exception to the bot admin user

    If the admin user is not found, this function does nothing
    """
    try:
        admin = await bot.fetch_user(CONFIG.ADMIN_USER_ID)
    except discord.NotFound:
        return

    tb = "".join(traceback.format_exception(error)).replace(
        CONFIG.BOT_TOKEN, "[REDACTED]"
    )
    await admin.send(
        embed=discord.Embed(
            title=f"Error: {type(error).__name__}",
            color=discord.Color.red(),
            description=f"```\n{tb[:4088]}```",
        )
    )


class Features(str, Enum):
    VOICE_ANNOUNCER = "voice_announcer"


async def has_features(*flags: Features, bot: discord.Client) -> bool:
    """Returns a boolean indicating if all of the features are enabled for the bot.

    Features are enabled by adding the literal flag value on a single line of
    the bot's description.
    """
    desc = await get_bot_description()
    logger.debug(f"Bot description: {desc!r}")

    enabled_flags = [c.strip() for c in desc.replace(":", ",").split(",")]
    return all(f.value in enabled_flags for f in flags)


def requires_features(*flags: Features):
    """Prevents a command from executing unless the given features are enabled.
    **This does not work with listeners. Use `has_features` instead.**

    Features are enabled by adding the literal flag value on a single line of
    the bot's bio.
    """

    async def _check(interaction: discord.Interaction) -> bool:
        return await has_features(*flags, bot=interaction.client)

    return app_commands.check(_check)
