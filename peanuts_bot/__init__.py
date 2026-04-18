import logging

import discord
from discord import app_commands
from discord.ext import commands

from peanuts_bot.config import CONFIG
from peanuts_bot.errors import handle_interaction_error
from peanuts_bot.extensions import ALL_EXTENSIONS
from peanuts_bot.extensions.internals import REQUIRED_EXTENSION_PROTOS

logger = logging.getLogger(__name__)


class _PeanutsTree(app_commands.CommandTree):
    async def on_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await handle_interaction_error(interaction, error)


class PeanutsBot(commands.Bot):
    async def setup_hook(self):
        for ext_info in ALL_EXTENSIONS:
            if ext_info.migrated:
                await self.load_extension(ext_info.module_path)

        for proto in REQUIRED_EXTENSION_PROTOS:
            for cog in self.cogs.values():
                if not isinstance(cog, proto):
                    raise RuntimeError(
                        f"{cog.__class__.__name__} does not implement {proto.__name__}"
                    )

        guild = discord.Object(id=CONFIG.GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        logger.info(f"Synced {len(synced)} commands: {[c.name for c in synced]}")

    async def on_ready(self) -> None:
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="/help")
        )


bot = PeanutsBot(
    command_prefix="!",
    intents=discord.Intents.all(),
    tree_cls=_PeanutsTree,
)
