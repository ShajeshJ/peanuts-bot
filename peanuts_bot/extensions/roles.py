from typing import Annotated
import interactions as ipy
import interactions.base as ipyb
import interactions.ext.enhanced as ipye

from config import CONFIG


class RolesExtension(ipy.Extension):
    def __init__(self, client: ipy.Client) -> None:
        self.client: ipy.Client = client

    base = ipyb

    @ipy.extension_command(name="role", scope=CONFIG.GUILD_ID)
    async def create_role(
        self,
        ctx: ipy.CommandContext,
        name: Annotated[str, ipye.EnhancedOption(description="Name of the new role")],
    ):
        """Create the given mention role"""
        await ctx.send(f"Received your command {name}")


def setup(client: ipy.Client):
    RolesExtension(client)
