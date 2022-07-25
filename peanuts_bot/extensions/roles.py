import logging
import asyncio
from typing import Annotated
import interactions as ipy
import interactions.ext.enhanced as ipye

from config import CONFIG

__all__ = ["setup", "RolesExtension"]

logger = logging.getLogger(__name__)

SELECT_JOIN_ROLE_ID = "join_role"


class RolesExtension(ipy.Extension):
    def __init__(self, client: ipy.Client) -> None:
        self.client: ipy.Client = client

    @ipy.extension_command(scope=CONFIG.GUILD_ID)
    async def role(self, _: ipy.CommandContext):
        pass

    @role.subcommand()
    @ipye.setup_options
    async def create(
        self,
        ctx: ipy.CommandContext,
        name: Annotated[
            str, ipye.EnhancedOption(str, description="Name of the new role")
        ],
    ):
        """Create a new mention role that others can join"""
        role = await ctx.guild.create_role(
            name=name,
            mentionable=True,
            reason=f"Mention role created via bot command by {ctx.author.name}",
            permissions=0,
        )
        await ctx.send(f"Created the role {role.mention}")

    @role.subcommand()
    @ipye.setup_options
    async def join(self, ctx: ipy.CommandContext):
        """Add yourself to a mention role"""
        options = [
            ipy.SelectOption(label=role.name, value=role.name)
            for role in await ctx.guild.get_all_roles()
            if is_joinable(role) and role.id not in ctx.author.roles
        ]
        if not options:
            await ctx.send("There are no new roles you can join")
            return

        role_dropdown = ipy.SelectMenu(
            custom_id=SELECT_JOIN_ROLE_ID,
            placeholder="Join a mention role",
            max_values=len(options),
            options=options,
        )
        await ctx.send(components=role_dropdown)

    @ipy.extension_component(SELECT_JOIN_ROLE_ID)
    async def join_selection(
        self, ctx: ipy.ComponentContext, role_names: list[str] | None
    ):
        """Callback after a selection is made on the join dropdown"""
        if not role_names:
            await ctx.send("Sorry, something went wrong. Try again later.")
            return

        invalid_roles = []
        joined_roles = {}

        valid_roles = {
            r.name: r for r in await ctx.guild.get_all_roles() if is_joinable(r)
        }

        for role_name in role_names:
            if role_name not in valid_roles:
                logger.info(f"{role_name} is not a joinable role. Skipping...")
                invalid_roles.append(role_name)
                continue

            if valid_roles[role_name].id in ctx.author.roles:
                # To avoid re-calling discord APIs to join roles the user is in
                logger.info(
                    f"{ctx.author.name} already joined {role_name}. Skipping..."
                )
                # Kind of hacky, but we're basically tagging on a "do nothing" task
                joined_roles[role_name] = asyncio.sleep(0)
                continue

            logger.info(f"{ctx.author.name} attempting to join {role_name}")
            joined_roles[role_name] = ctx.author.add_role(
                valid_roles[role_name], ctx.guild_id
            )

        await asyncio.gather(*joined_roles.values())

        if joined_roles:
            await ctx.send(f"Successfully joined {', '.join(joined_roles)}")

        if invalid_roles:
            await ctx.send(f"Failed to join {', '.join(invalid_roles)}.")


def is_joinable(r: ipy.Role) -> bool:
    return r.mentionable and r.permissions == "0"


def setup(client: ipy.Client):
    RolesExtension(client)
