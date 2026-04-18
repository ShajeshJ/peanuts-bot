from collections.abc import Iterator
import re
import typing

import discord


_DisableableItem = (
    discord.ui.Button
    | discord.ui.Select
    | discord.ui.UserSelect
    | discord.ui.RoleSelect
    | discord.ui.ChannelSelect
    | discord.ui.MentionableSelect
)


def _is_disableable(
    item: discord.ui.Item[discord.ui.View],
) -> typing.TypeGuard[_DisableableItem]:
    return isinstance(
        item,
        (
            discord.ui.Button,
            discord.ui.Select,
            discord.ui.UserSelect,
            discord.ui.RoleSelect,
            discord.ui.ChannelSelect,
            discord.ui.MentionableSelect,
        ),
    )


# Try to match discord message link https://discord.com/channels/<id>/<id>/<id>
_DISCORD_MSG_URL_REGEX = (
    r"https?:\/\/discord\.com"
    r"\/channels\/(?P<g_id>[0-9]+)"
    r"\/(?P<c_id>[0-9]+)"
    r"\/(?P<m_id>[0-9]+)"
)


class DiscordMesageLink(typing.NamedTuple):
    guild_id: int
    channel_id: int
    message_id: int

    @property
    def url(self) -> str:
        return f"https://discord.com/channels/{self.guild_id}/{self.channel_id}/{self.message_id}"


BAD_TWITTER_LINKS = ["https://twitter.com", "https://x.com"]


def is_messagable(
    channel: object,
) -> typing.TypeGuard[discord.abc.Messageable]:
    """
    Type guard to check if a channel is messageable

    :param channel: The channel to check
    :return: True if the channel is messageable, False otherwise
    """
    return isinstance(channel, discord.abc.Messageable)


async def disable_message_components(
    msg: discord.Message | None,
) -> discord.Message | None:
    """
    Edits the given message to disable all components

    :param msg: The message to disable components for
    :return: The edited message, or None if the message was None
    """
    if msg is None or not msg.components:
        return msg

    view = discord.ui.View.from_message(msg, timeout=None)
    for child in view.children:
        if _is_disableable(child):
            child.disabled = True
    return await msg.edit(view=view)


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


def parse_discord_msg_link(link: str) -> DiscordMesageLink | None:
    """
    Parses a discord message link into a DiscordMesageLink object

    :param link: The link to parse
    :return: The parsed link or None if the link is invalid
    """
    return next(get_discord_msg_links(link), None)
