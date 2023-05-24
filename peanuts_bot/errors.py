import logging

import interactions as ipy
from peanuts_bot.constants.bot import SOMETHING_WRONG

logger = logging.getLogger(__name__)


class BotUsageError(Exception):
    """An exception to raise when you want to surface a specific user error messages"""

    pass


@ipy.listen(disable_default_listeners=True)
async def on_command_error(event: ipy.events.CommandError):
    """
    Error handler for all bot commands
    """
    if not isinstance(event.ctx, ipy.InteractionContext):
        raise Exception(
            f"did not get InteractionContext; instead got {type(event.ctx).__name__}"
        ) from event.error

    if isinstance(event.error, BotUsageError):
        await event.ctx.send(str(event.error), ephemeral=True)
        return

    try:
        await event.ctx.send(SOMETHING_WRONG, ephemeral=True)
    except Exception as e:
        raise e from event.error

    raise event.error
