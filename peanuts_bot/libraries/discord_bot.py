from collections.abc import Iterator
from dataclasses import dataclass
import re
from typing import TypeVar
import interactions as ipy

# Try to match discord message link https://discord.com/channels/<id>/<id>/<id>
_DISCORD_MSG_URL_REGEX = r"https?:\/\/discord\.com\/channels\/[0-9]+\/[0-9]+\/[0-9]+"


def get_discord_msg_urls(content: str) -> Iterator[str]:
    """
    Returns a list of all discord message links in the given content

    :param content: The content to search for links
    :return: A list of all discord message urls found in the content
    """
    for url in re.finditer(_DISCORD_MSG_URL_REGEX, content):
        yield url.group(0)


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
