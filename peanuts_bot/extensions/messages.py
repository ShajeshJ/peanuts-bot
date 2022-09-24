from dataclasses import astuple, dataclass
import logging
import random
import re
from typing import Annotated
import interactions as ipy
import interactions.ext.enhanced as ipye

from config import CONFIG
from peanuts_bot.errors import BotUsageError
from peanuts_bot.libraries.discord_bot import AutoCompletion

__all__ = ["setup", "MessagesExtension"]

logger = logging.getLogger(__name__)


DICE_NOTATION = re.compile(r"(?P<num>\d*)d(?P<max>\d+)(?P<shift>((\+|-)[0-9]+)?)")


@dataclass
class DiceArgs:
    num: int
    max: int
    shift: int


def parse_dice_args(notation: str) -> DiceArgs:
    """Parse a given notation string

    :param notation: The dice roll notation
    :return: The parsed dice roll arguments
    """
    notation = notation.replace(" ", "")
    match = re.fullmatch(DICE_NOTATION, notation)

    if not match:
        raise BotUsageError(
            "Invalid dice notation. Example valid notation: d6, 3d6, 3d6+4"
        )

    d_args = match.groupdict()
    return DiceArgs(
        int(d_args["num"] or 1),
        int(d_args["max"]),
        int(d_args["shift"] or 0),
    )


class MessagesExtension(ipy.Extension):
    def __init__(self, client: ipy.Client) -> None:
        self.client: ipy.Client = client

    @ipy.extension_command(scope=CONFIG.GUILD_ID)
    @ipye.setup_options
    async def roll(
        self,
        ctx: ipy.CommandContext,
        notation: Annotated[
            str,
            ipye.EnhancedOption(
                str, description="D&D style dice notation (Adx+y)", autocomplete=True
            ),
        ],
    ):
        """Perform a dice roll"""
        num, max, shift = astuple(parse_dice_args(notation))

        if shift > 0:
            shift_str = f"+{shift}"
        elif shift < 0:
            shift_str = f"-{shift*-1}"
        else:
            shift_str = ""

        values = [str(random.choice(range(max)) + 1 + shift) for _ in range(num)]
        await ctx.send(
            f"Rolling `(1 - {max}){shift_str}`, {num} times:\n```{', '.join(values)}```"
        )

    @roll.autocomplete("notation")
    async def notation(self, ctx: ipy.CommandContext, user_input: str = ""):
        """Autocompletion for the `notation` option for the `roll` command"""
        user_input = user_input.replace(" ", "")
        if re.fullmatch(DICE_NOTATION, user_input):
            await ctx.populate(AutoCompletion(user_input))
            return

        await ctx.populate(AutoCompletion("invalid notation"))


def setup(client: ipy.Client):
    MessagesExtension(client)
