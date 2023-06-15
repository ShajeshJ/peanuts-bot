from collections.abc import Iterator
import re
from typing import NamedTuple
import interactions as ipy

# Try to match discord message link https://discord.com/channels/<id>/<id>/<id>
_DISCORD_MSG_URL_REGEX = (
    r"https?:\/\/discord\.com"
    r"\/channels\/(?P<g_id>[0-9]+)"
    r"\/(?P<c_id>[0-9]+)"
    r"\/(?P<m_id>[0-9]+)"
)


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


def has_admin_permission(p: ipy.Permissions | None) -> bool:
    return bool(p is not None and p & ipy.Permissions.ADMINISTRATOR)
