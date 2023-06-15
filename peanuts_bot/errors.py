import logging
import traceback

import interactions as ipy

from config import CONFIG

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

        # Also notify admin user of the error
        admin = await event.bot.fetch_user(CONFIG.ADMIN_USER_ID)
        if admin:
            tb = "".join(traceback.format_exception(event.error)).replace(
                CONFIG.BOT_TOKEN, "[REDACTED]"
            )
            await admin.send(
                embeds=ipy.Embed(
                    title=f"Error: {type(event.error).__name__}",
                    color=ipy.BrandColors.RED,
                    description=f"```\n{tb[:ipy.EMBED_MAX_DESC_LENGTH - 8]}```",
                ),
                ephemeral=True,
            )

    except Exception as e:
        raise e from event.error

    raise event.error
