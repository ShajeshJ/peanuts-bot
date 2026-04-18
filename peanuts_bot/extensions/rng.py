import logging
import random
import re
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from peanuts_bot.errors import BotUsageError, handle_interaction_error
from peanuts_bot.libraries.tabletop_roller import DiceRoll, parse_dice_roll

__all__ = ["RngExtension"]

logger = logging.getLogger(__name__)

_RANDOM_BUTTON_TEMPLATE = r"random_(?P<min>-?\d+)_(?P<max>-?\d+)"
_ROLL_BUTTON_TEMPLATE = r"roll_(?P<roll>[+-]?\d*d\d+(?:[+-]\d+)?)"


def _append_new_result(msg: str, result: str, is_first: bool = False) -> str:
    if not is_first:
        msg = msg.rstrip("*\n`")
    return f"{msg}\n{result}{('*' if not is_first else '')}\n```"


class RandomButton(
    discord.ui.DynamicItem[discord.ui.Button], template=_RANDOM_BUTTON_TEMPLATE
):
    def __init__(self, min_val: int, max_val: int):
        super().__init__(
            discord.ui.Button(
                label="Randomize Again",
                style=discord.ButtonStyle.primary,
                custom_id=f"random_{min_val}_{max_val}",
            )
        )
        self.min_val = min_val
        self.max_val = max_val

    @classmethod
    async def from_custom_id(
        cls,
        interaction: discord.Interaction,
        item: discord.ui.Item[Any],
        match: re.Match[str],
    ) -> "RandomButton":
        return cls(int(match["min"]), int(match["max"]))

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.message:
            return
        content = _append_new_result(
            interaction.message.content,
            str(random.randint(self.min_val, self.max_val)),
        )
        await interaction.response.edit_message(content=content)

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        await handle_interaction_error(interaction, error)


class RollButton(
    discord.ui.DynamicItem[discord.ui.Button], template=_ROLL_BUTTON_TEMPLATE
):
    def __init__(self, roll: DiceRoll):
        super().__init__(
            discord.ui.Button(
                label="Roll Again",
                style=discord.ButtonStyle.primary,
                custom_id=f"roll_{roll}",
            )
        )
        self.roll = roll

    @classmethod
    async def from_custom_id(
        cls,
        interaction: discord.Interaction,
        item: discord.ui.Item[Any],
        match: re.Match[str],
    ) -> "RollButton":
        return cls(parse_dice_roll(match["roll"]))

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.message:
            return
        rolled_dice = [
            random.randint(1, self.roll.sides) for _ in range(self.roll.count)
        ]
        result = sum(rolled_dice) + self.roll.modifier
        content = _append_new_result(
            interaction.message.content,
            f"Rolls: {rolled_dice} | Result: {result}",
        )
        await interaction.response.edit_message(content=content)

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        await handle_interaction_error(interaction, error)


class RngExtension(commands.Cog):
    @staticmethod
    def get_help_color() -> discord.Color:
        return discord.Color.from_str("#E67E22")

    @app_commands.command()
    @app_commands.describe(
        min="Minimum (inclusive) value of the random number",
        max="Maximum (inclusive) value of the random number",
    )
    async def random(
        self, interaction: discord.Interaction, min: int, max: int
    ) -> None:
        """Generate a random number between two values"""
        if min > max:
            raise BotUsageError("Minimum value cannot be greater than maximum value")

        content = _append_new_result(
            msg=f"Randomize ({min} to {max}):\n```",
            result=str(random.randint(min, max)),
            is_first=True,
        )
        view = discord.ui.View()
        view.add_item(RandomButton(min, max))
        await interaction.response.send_message(content, view=view)

    @app_commands.command()
    @app_commands.describe(roll="A dice roll to execute (e.g. 1d20+5)")
    async def roll(self, interaction: discord.Interaction, roll: str) -> None:
        """Roll dice and calculate the results using dice notation for most tabletop games"""
        try:
            parsed_roll = parse_dice_roll(roll)
        except ValueError:
            raise BotUsageError(f"Invalid dice roll '{roll}'")

        rolled_dice = [
            random.randint(1, parsed_roll.sides) for _ in range(parsed_roll.count)
        ]
        result = sum(rolled_dice) + parsed_roll.modifier

        content = _append_new_result(
            msg=f"Rolling {parsed_roll}:\n```",
            result=f"Rolls: {rolled_dice} | Result: {result}",
            is_first=True,
        )
        view = discord.ui.View()
        view.add_item(RollButton(parsed_roll))
        await interaction.response.send_message(content, view=view)


async def setup(bot: commands.Bot) -> None:
    bot.add_dynamic_items(RandomButton, RollButton)
    await bot.add_cog(RngExtension())
