import discord
from discord.ext import commands

from peanuts_bot.config import CONFIG
from peanuts_bot.errors import BotUsageError, handle_interaction_error
from peanuts_bot.extensions.internals import REQUIRED_EXTENSION_PROTOS


class PeanutsBot(commands.Bot):
    async def setup_hook(self):
        # Extensions loaded here in Step 2+

        for proto in REQUIRED_EXTENSION_PROTOS:
            for cog in self.cogs.values():
                if not isinstance(cog, proto):
                    raise RuntimeError(
                        f"{cog.__class__.__name__} does not implement {proto.__name__}"
                    )

        guild = discord.Object(id=CONFIG.GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_ready(self):
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="/help")
        )

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
    ):
        await handle_interaction_error(interaction, error)


bot = PeanutsBot(
    command_prefix="!",
    intents=discord.Intents.all(),
)
