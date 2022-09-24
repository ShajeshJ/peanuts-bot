import interactions as ipy


class AutoCompletion(ipy.Choice):
    """Small wrapper to simplify auto completion choices"""

    def __init__(self, val: str):
        super().__init__(name=val, value=val)


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
