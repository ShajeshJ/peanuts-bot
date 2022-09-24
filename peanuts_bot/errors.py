import logging

import interactions as ipy
from peanuts_bot.constants.bot import SOMETHING_WRONG

logger = logging.getLogger(__name__)


class BotUsageError(Exception):
    """An exception to raise when you want to surface a specific user error messages"""

    pass


async def global_error_handler(
    ctx: ipy.CommandContext | ipy.ComponentContext, e: Exception
):
    """
    Global error handler for the bot; can be used to handle command and component errors
    """

    if isinstance(e, BotUsageError):
        await ctx.send(str(e), ephemeral=True)
        return

    try:
        await ctx.send(SOMETHING_WRONG, ephemeral=True)
    except Exception as e:
        logger.warning(str(e))

    raise e
