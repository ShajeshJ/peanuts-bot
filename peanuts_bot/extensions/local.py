from typing import Annotated
import interactions as ipy

from peanuts_bot.config import CONFIG
from peanuts_bot.extensions import ALL_EXTENSIONS


class LocalExtension(ipy.Extension):
    """Commands to improve local development only"""

    @staticmethod
    def get_help_color() -> ipy.Color:
        return ipy.FlatUIColors.ASBESTOS

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
                choices=[e.to_slash_command_choice() for e in ALL_EXTENSIONS],
            ),
        ],
    ):
        """[ADMIN-ONLY] Reload bot commands"""

        # TODO: Submit extension unloading fix for patterned callbacks
        self.bot.reload_extension(ext)
        await ctx.send(f"{ext} reloaded", ephemeral=True)
