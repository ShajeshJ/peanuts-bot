from typing import Annotated
import interactions as ipy
import interactions.base as ipyb
import interactions.ext.enhanced as ipye

from config import CONFIG


class RolesExtension(ipy.Extension):
    def __init__(self, client: ipy.Client) -> None:
        self.client: ipy.Client = client

    base = ipyb

    @ipy.extension_command(
        name="role",
        scope=CONFIG.GUILD_ID,
        options=[
            ipy.Option(
                name="name",
                description="Name of the new role",
                type=ipy.OptionType.STRING,
                required=True,
            )
        ],
    )
    async def create_role(
        self,
        ctx: ipy.CommandContext,
        name: str,  # Annotated[str, ipy.Option(description="Name of the new role")],
    ):
        """Create a new mention role"""
        role = await ctx.guild.create_role(
            name,
            mentionable=True,
            reason=f"Mention role created via bot command by {ctx.author.name}",
            permissions=0,
        )
        await ctx.send(f"Created the role {role.mention}")


def setup(client: ipy.Client):
    RolesExtension(client)
