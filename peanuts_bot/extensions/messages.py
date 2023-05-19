import logging
import random
import re
from typing import Annotated
import interactions as ipy
import interactions.ext.enhanced as ipye

from config import CONFIG
from peanuts_bot.errors import BotUsageError

__all__ = ["setup", "MessagesExtension"]

logger = logging.getLogger(__name__)


RANDOM_PREFIX = "random_"
RANDOM_BUTTON_REGEX = re.compile(f"^{RANDOM_PREFIX}(?P<min>-?\\d+)_(?P<max>-?\\d+)$")


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

        await ctx.send(
            f"Randomize ({min} to {max}):\n```\n{random.randint(min, max)}\n```",
            components=[get_random_button(min, max)],
        )

    @ipy.extension_component(RANDOM_PREFIX, startswith=True)
    async def rerun_random(self, ctx: ipy.ComponentContext):
        """Re-run the random command with the same parameters"""
        if not ctx.custom_id or not ctx.message:
            return

        min, max = parse_random_id(ctx.custom_id)
        new_msg = ctx.message.content.rstrip("*\n`")
        new_msg += f"\n{random.randint(min, max)}*\n```"
        await ctx.edit(new_msg, components=ctx.message.components)

    @ipy.extension_command(scope=CONFIG.GUILD_ID)
    @ipye.setup_options
    async def roll(
        self,
        ctx: ipy.CommandContext,
        max: Annotated[
            int,
            ipye.EnhancedOption(
                int, description="Maximum value on the dice", min_value=1
            ),
        ],
        num_dice: Annotated[
            int,
            ipye.EnhancedOption(int, description="Number of dice to roll", min_value=1),
        ] = 1,
        modifier: Annotated[
            int,
            ipye.EnhancedOption(int, description="Value to add to the final sum"),
        ] = 0,
    ):
        """Roll dice and calculate results, as in a tabletop game"""

        results = [random.randint(1, max) for _ in range(num_dice)]
        if modifier < 0:
            modifier_str = f" - {-modifier}"
        elif modifier > 0:
            modifier_str = f" + {modifier}"
        else:
            modifier_str = ""
        await ctx.send(
            f"```\nRolling {num_dice}d{max}{modifier_str}:\n{', '.join(map(str, results))}\n= {sum(results) + modifier}```"
        )


def get_random_button(min: int, max: int) -> ipy.Button:
    return ipy.Button(
        label="Randomize Again",
        custom_id=f"{RANDOM_PREFIX}{min}_{max}",
        style=ipy.ButtonStyle.PRIMARY,
    )


def parse_random_id(custom_id: str) -> tuple[int, int]:
    match = RANDOM_BUTTON_REGEX.match(custom_id)
    if not match:
        raise ValueError(f"Invalid random button ID '{custom_id}'")

    return int(match["min"]), int(match["max"])


def setup(client: ipy.Client):
    MessagesExtension(client)
