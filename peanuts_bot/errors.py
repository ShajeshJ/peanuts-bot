import logging
import traceback

import discord
from discord import app_commands

from peanuts_bot.config import CONFIG
from peanuts_bot.libraries.discord.admin import send_error_to_admin

logger = logging.getLogger(__name__)
SOMETHING_WRONG = "Sorry, something went wrong. Try again later."


class BotUsageError(Exception):
    """An exception to raise when you want to surface a specific user error messages"""

    ...


async def handle_interaction_error(
    interaction: discord.Interaction, error: Exception
) -> None:
    """Shared error handler for slash commands and View callbacks"""
    cause = getattr(error, "__cause__", error)

    async def _send(msg: str) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

    if isinstance(cause, BotUsageError):
        await _send(str(cause))
        return

    try:
        await _send(SOMETHING_WRONG)
        await send_error_to_admin(cause, interaction.client)
    except Exception as e:
        raise e from cause

    raise cause
