import logging
from typing import Annotated
import interactions as ipy
import interactions.ext.enhanced as ipye

from config import CONFIG
from peanuts_bot.errors import BotUsageError

__all__ = ["setup", "MessagesExtension"]

logger = logging.getLogger(__name__)


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
                str, description="D&D style dice notation", autocomplete=True
            ),
        ],
    ):
        """Perform a dice roll"""
        await ctx.send("Performing main command dice roll")

    @roll.autocomplete("notation")
    async def notation(self, ctx: ipy.CommandContext, user_input: str = ""):
        """Autocompletion for the `notation` option for the `roll` command"""
        await ctx.populate(ipy.Choice(name="1d6+0", value="1d6+0"))


def setup(client: ipy.Client):
    MessagesExtension(client)
