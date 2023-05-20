from collections.abc import Iterator
from dataclasses import dataclass
import re
from typing import TypeVar
import interactions as ipy

# Try to match discord message link
_DISCORD_MSG_URL_REGEX = (
    "https?:\\/\\/discord\\.com\\/channels\\/"
    "(?P<g_id>[0-9]+)\\/"
    "(?P<c_id>[0-9]+)\\/"
    "(?P<m_id>[0-9]+)"
)


DiscT = TypeVar("DiscT", bound=ipy.IDMixin)


def get_by_id(obj_id: int, obj_list: list[DiscT]) -> DiscT:
    """
    Returns the discord object from the list with the given ID

    :param obj_id: The ID of the object to return
    :param obj_list: The list of objects to search
    :return: The object with the given ID
    """
    try:
        return next(o for o in obj_list if o.id == obj_id)
    except StopIteration:
        raise ValueError(
            f"No {DiscT.__class__.__name__} found with ID {obj_id} in the list"
        )


def get_guild(guild_id: int, client: ipy.Client) -> ipy.Guild:
    """
    Returns the guild object that the bot is currently in

    :param client: The client object
    :return: The guild object
    """
    try:
        return next(g for g in client.guilds if g.id == guild_id)
    except StopIteration:
        raise ValueError(f"Bot is not in guild {guild_id}")


@dataclass(frozen=True)
class DiscordMessageLink:
    guild_id: int
    channel_id: int
    message_id: int

    def __str__(self):
        return f"https://discord.com/channels/{self.guild_id}/{self.channel_id}/{self.message_id}"

    @classmethod
    def from_url(cls, url: str):
        match = re.match(_DISCORD_MSG_URL_REGEX, url)
        if not match:
            raise ValueError(f"Invalid discord message url: {url}")

        return cls(
            guild_id=int(match.group("g_id")),
            channel_id=int(match.group("c_id")),
            message_id=int(match.group("m_id")),
        )

    @classmethod
    def from_message(cls, message: ipy.Message):
        return cls(
            guild_id=message.guild_id,
            channel_id=message.channel_id,
            message_id=message.id,
        )


def get_discord_msg_links(content: str) -> Iterator[DiscordMessageLink]:
    """
    Returns a list of all discord message links in the given content

    :param content: The content to search for links
    :return: A list of all discord message links in the content
    """
    for url in re.finditer(_DISCORD_MSG_URL_REGEX, content):
        yield DiscordMessageLink(
            guild_id=int(url.group("g_id")),
            channel_id=int(url.group("c_id")),
            message_id=int(url.group("m_id")),
        )


def disable_all_components(
    component_rows: list[ipy.ActionRow] | None,
) -> list[ipy.ActionRow] | None:
    """
    Disables all components in the given component sets

    :param component_rows: The set of components to disable
    :return: The same component row objects, but with individual components disabled
    """

    if component_rows is None:
        return None

    for row in component_rows:
        if row.components is None:
            continue

        for component in row.components:
            component.disabled = True

    return component_rows


def get_emoji_mention(emoji: ipy.Emoji) -> str:
    """
    Return the mention of an emoji so it can be printed in discord

    :param emoji: The emoji to print
    :return: A string representing the "mention" value of the emoji
    """
    return f"<:{emoji.name}:{emoji.id}>"
