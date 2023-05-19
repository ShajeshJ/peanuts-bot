import logging
import random
import re
from typing import Annotated
import interactions as ipy
import interactions.ext.enhanced as ipye

from config import CONFIG
from peanuts_bot.errors import BotUsageError
from peanuts_bot.libraries.tabletop_roller import DiceRoll, parse_dice_roll

__all__ = ["setup", "MessagesExtension"]

logger = logging.getLogger(__name__)


RANDOM_BUTTON_PREFIX = "random_"
RANDOM_BUTTON_REGEX = re.compile(
    f"^{RANDOM_BUTTON_PREFIX}(?P<min>-?\\d+)_(?P<max>-?\\d+)$"
)
ROLL_BUTTON_PREFIX = "roll_"


def get_random_button(min: int, max: int) -> ipy.Button:
    return ipy.Button(
        label="Randomize Again",
        custom_id=f"{RANDOM_BUTTON_PREFIX}{min}_{max}",
        style=ipy.ButtonStyle.PRIMARY,
    )


def parse_random_button_id(custom_id: str) -> tuple[int, int]:
    match = RANDOM_BUTTON_REGEX.match(custom_id)
    if not match:
        raise ValueError(f"Invalid random button ID '{custom_id}'")

    return int(match["min"]), int(match["max"])


def get_roll_button(roll: DiceRoll) -> ipy.Button:
    return ipy.Button(
        label="Roll Again",
        custom_id=f"{ROLL_BUTTON_PREFIX}{roll}",
        style=ipy.ButtonStyle.PRIMARY,
    )


def append_new_result(msg: str, result: str, is_first: bool = False) -> str:
    """Helper method to append a new result to the end
    of the code block in the message content
    """
    if not is_first:
        msg = msg.rstrip("*\n`")
    return f"{msg}\n{result}{('*' if not is_first else '')}\n```"


class MessagesExtension(ipy.Extension):
    def __init__(self, client: ipy.Client) -> None:
        self.client: ipy.Client = client

    @ipy.extension_command(scope=CONFIG.GUILD_ID)
    @ipye.setup_options
    async def random(
        self,
        ctx: ipy.CommandContext,
        min: Annotated[
            int,
            ipye.EnhancedOption(
                int, description="Minimum (inclusive) value of the random number"
            ),
        ],
        max: Annotated[
            int,
            ipye.EnhancedOption(
                int, description="Maximum (inclusive) value of the random number"
            ),
        ],
    ):
        """Generate a random number between two values"""

        if min > max:
            raise BotUsageError("Minimum value cannot be greater than maximum value")

        content = append_new_result(
            msg=f"Randomize ({min} to {max}):\n```",
            result=random.randint(min, max),
            is_first=True,
        )
        await ctx.send(content, components=[get_random_button(min, max)])

    @ipy.extension_component(RANDOM_BUTTON_PREFIX, startswith=True)
    async def rerun_random(self, ctx: ipy.ComponentContext):
        """Re-run the random command with the same parameters"""
        if not ctx.custom_id or not ctx.message:
            return

        min, max = parse_random_button_id(ctx.custom_id)
        content = append_new_result(ctx.message.content, random.randint(min, max))
        await ctx.edit(content, components=ctx.message.components)

    @ipy.extension_command(scope=CONFIG.GUILD_ID)
    @ipye.setup_options
    async def roll(
        self,
        ctx: ipy.CommandContext,
        roll: Annotated[
            str,
            ipye.EnhancedOption(
                str,
                description="A dice roll to execute (e.g. 1d20+5)",
            ),
        ],
    ):
        """Roll dice and calculate the results using dice notation for most tabletop games"""

        try:
            parsed_roll = parse_dice_roll(roll)
        except ValueError:
            raise BotUsageError(f"Invalid dice roll '{roll}'")

        rolled_dice = [
            random.randint(1, parsed_roll.sides) for _ in range(parsed_roll.count)
        ]
        result = sum(rolled_dice) + parsed_roll.modifier

        content = append_new_result(
            msg=f"Rolling {parsed_roll}:\n```",
            result=f"Rolls: {rolled_dice} | Result: {result}",
            is_first=True,
        )
        await ctx.send(content, components=[get_roll_button(parsed_roll)])

    @ipy.extension_component(ROLL_BUTTON_PREFIX, startswith=True)
    async def rerun_roll(self, ctx: ipy.ComponentContext):
        """Re-run the roll command with the same parameters"""
        if not ctx.custom_id or not ctx.message:
            return

        roll = ctx.custom_id.replace(ROLL_BUTTON_PREFIX, "")
        try:
            parsed_roll = parse_dice_roll(roll)
        except ValueError:
            raise BotUsageError(f"Invalid dice roll '{roll}'")

        rolled_dice = [
            random.randint(1, parsed_roll.sides) for _ in range(parsed_roll.count)
        ]
        result = sum(rolled_dice) + parsed_roll.modifier

        content = append_new_result(
            msg=ctx.message.content, result=f"Rolls: {rolled_dice} | Result: {result}"
        )
        await ctx.edit(content, components=ctx.message.components)


def setup(client: ipy.Client):
    MessagesExtension(client)