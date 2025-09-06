from collections.abc import Iterator
from contextlib import asynccontextmanager
from enum import Enum
import logging
import re
import traceback
from typing import NamedTuple
import typing
import aiohttp
import interactions as ipy

from peanuts_bot.config import CONFIG


logger = logging.getLogger(__name__)


# Try to match discord message link https://discord.com/channels/<id>/<id>/<id>
_DISCORD_MSG_URL_REGEX = (
    r"https?:\/\/discord\.com"
    r"\/channels\/(?P<g_id>[0-9]+)"
    r"\/(?P<c_id>[0-9]+)"
    r"\/(?P<m_id>[0-9]+)"
)

BAD_TWITTER_LINKS = ["https://twitter.com", "https://x.com"]


class DiscordMesageLink(NamedTuple):
    guild_id: int
    channel_id: int
    message_id: int

    @property
    def url(self) -> str:
        return f"https://discord.com/channels/{self.guild_id}/{self.channel_id}/{self.message_id}"


def parse_discord_msg_link(link: str) -> DiscordMesageLink | None:
    """
    Parses a discord message link into a DiscordMesageLink object

    :param link: The link to parse
    :return: The parsed link or None if the link is invalid
    """
    return next(get_discord_msg_links(link), None)


def get_discord_msg_links(content: str) -> Iterator[DiscordMesageLink]:
    """
    Gets all discord message links in the content

    :param content: The content to search for links
    :return: A iterable of all discord message links found in the content
    """
    for url in re.finditer(_DISCORD_MSG_URL_REGEX, content):
        parsed_values = url.groupdict()
        yield DiscordMesageLink(
            int(parsed_values["g_id"]),
            int(parsed_values["c_id"]),
            int(parsed_values["m_id"]),
        )


async def disable_message_components(msg: ipy.Message | None) -> ipy.Message | None:
    """
    Edits the given message to disable all components

    :param msg: The message to disable components for
    :return: The edited message, or None if the message was None
    """

    if msg is None:
        return None

    if not msg.components:
        return msg

    return await msg.edit(
        components=ipy.utils.misc_utils.disable_components(*msg.components)
    )


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


def is_messagable(
    channel: ipy.BaseChannel | None,
) -> typing.TypeGuard[ipy.TYPE_MESSAGEABLE_CHANNEL]:
    """
    Type guard to check if a channel is messageable

    :param channel: The channel to check
    :return: True if the channel is messageable, False otherwise
    """
    return isinstance(channel, typing.get_args(ipy.TYPE_MESSAGEABLE_CHANNEL))


class Features(str, Enum):
    VOICE_ANNOUNCER = "voice_announcer"


def requires_features(*flags: Features):
    """Prevents a command from executing unless the given features are enabled.
    **This does not work with listeners. Use `has_features` instead.**

    Features are enabled by adding the literal flag value on a single line of
    the bot's bio.
    """

    async def _check(ctx: ipy.BaseContext) -> bool:
        return await has_features(*flags, guild=ctx.guild)

    return ipy.check(_check)


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


async def get_bot_description() -> str:
    try:
        async with get_api_session() as session:
            async with session.get("applications/@me") as response:
                response.raise_for_status()
                data = await response.json()

        return data.get("description", "")
    except:
        logger.warning("failed to fetch bot description", exc_info=True)
        return ""


@asynccontextmanager
async def get_api_session():
    async with aiohttp.ClientSession(
        "https://discord.com/api/v10/",
        headers={"Authorization": f"Bot {CONFIG.BOT_TOKEN}"},
    ) as session:
        yield session
