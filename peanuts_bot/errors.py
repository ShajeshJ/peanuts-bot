import logging
import traceback

import interactions as ipy

from peanuts_bot.config import CONFIG
from peanuts_bot.libraries.discord.admin import send_error_to_admin

logger = logging.getLogger(__name__)
SOMETHING_WRONG = "Sorry, something went wrong. Try again later."


class BotUsageError(Exception):
    """An exception to raise when you want to surface a specific user error messages"""

    ...


@ipy.listen(disable_default_listeners=True)
async def on_error(event: ipy.events.Error):
    """
    Fallback global error handler
    """
    if not isinstance(event.ctx, ipy.InteractionContext):
        raise Exception(
            f"did not get InteractionContext for {event.source}; instead got {type(event.ctx).__name__}"
        ) from event.error

    if isinstance(event.error, BotUsageError):
        await event.ctx.send(str(event.error), ephemeral=True)
        return

    try:
        await event.ctx.send(SOMETHING_WRONG, ephemeral=True)
        await send_error_to_admin(event.error, event.bot)
    except Exception as e:
        raise e from event.error

    raise event.error
