from enum import Enum
import traceback

import interactions as ipy

from peanuts_bot.config import CONFIG


async def send_error_to_admin(error: Exception, bot: ipy.Client):
    """Forwards the exception to the bot admin user

    If the admin user is not found, this function does nothing
    """

    admin = await bot.fetch_user(CONFIG.ADMIN_USER_ID)
    if not admin:
        return

    tb = "".join(traceback.format_exception(error)).replace(
        CONFIG.BOT_TOKEN, "[REDACTED]"
    )
    await admin.send(
        embeds=ipy.Embed(
            title=f"Error: {type(error).__name__}",
            color=ipy.BrandColors.RED,
            description=f"```\n{tb[:ipy.EMBED_MAX_DESC_LENGTH - 8]}```",
        ),
        ephemeral=True,
    )


class Features(str, Enum):
    VOICE_ANNOUNCER = "voice_announcer"


async def has_features(*flags: Features, guild: ipy.Guild | None) -> bool:
    """Returns a boolean indicating if all of the features are enabled for the guild.

    For convenience, this method will accept `None` for the guild value, but will
    always return False if no guild is passed in.

    Features are enabled by adding the literal flag value on a single line of
    the guild's description.
    """

    desc = (guild and guild.description) or ""
    if not desc:
        return False

    enabled_flags = [c.strip() for c in desc.replace(":", ",").split(",")]
    return all(f.value in enabled_flags for f in flags)


def requires_features(*flags: Features):
    """Prevents a command from executing unless the given features are enabled.
    **This does not work with listeners. Use `has_features` instead.**

    Features are enabled by adding the literal flag value on a single line of
    the bot's bio.
    """

    async def _check(ctx: ipy.BaseContext) -> bool:
        return await has_features(*flags, guild=ctx.guild)

    return ipy.check(_check)
