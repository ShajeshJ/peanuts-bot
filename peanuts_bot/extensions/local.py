import discord
from discord import app_commands
from discord.ext import commands

from peanuts_bot.extensions import ALL_EXTENSIONS

__all__ = ["LocalExtension"]


class LocalExtension(commands.Cog):
    """Commands to improve local development only"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    def get_help_color() -> discord.Color:
        return discord.Color.from_str("#95A5A6")

    @app_commands.command(name="reload")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(
        ext=[
            app_commands.Choice(name=e.ext_name, value=e.module_path)
            for e in ALL_EXTENSIONS
            if e.migrated
        ]
    )
    async def reload(self, interaction: discord.Interaction, ext: str) -> None:
        """[ADMIN-ONLY] Reload bot commands"""

        await self.bot.reload_extension(ext)
        await interaction.response.send_message(f"{ext} reloaded", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LocalExtension(bot))
