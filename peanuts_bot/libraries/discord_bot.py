from collections.abc import Iterator
import re
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

    return ipy.utils.misc_utils.disable_components(*component_rows)
