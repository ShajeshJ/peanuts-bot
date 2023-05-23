from typing import Annotated
import interactions as ipy

from config import CONFIG
from peanuts_bot.extensions import ALL_EXTENSIONS


class LocalExtension(ipy.Extension):
    """Commands to improve local development only"""

    @ipy.slash_command(
        scopes=[CONFIG.GUILD_ID],
        default_member_permissions=ipy.Permissions.ADMINISTRATOR,
    )
    async def reload(
        self,
        ctx: ipy.SlashContext,
        ext: Annotated[
            str,
            ipy.slash_str_option(
                required=True,
                description="The extension to reload",
                choices=ALL_EXTENSIONS,
            ),
        ],
    ):
        """[ADMIN-ONLY] Reload bot commands"""
        # bot.reload_extension(ext)
        await ctx.send(f"{ext} reloaded", ephemeral=True)
