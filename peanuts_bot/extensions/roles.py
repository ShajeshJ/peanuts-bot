import logging
import asyncio
from typing import Annotated
import interactions as ipy
import interactions.ext.enhanced as ipye

from config import CONFIG

__all__ = ["setup", "RolesExtension"]

logger = logging.getLogger(__name__)

ROLE_TOGGLE_PREFIX = "role_toggle_"


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

        if any(r.name == name for r in await ctx.guild.get_all_roles()):
            await ctx.send(f"The role {name} already exists", ephemeral=True)
            return

        role = await ctx.guild.create_role(
            name=name,
            mentionable=True,
            reason=f"Created by {ctx.author.name} via bot commands",
            permissions=0,
        )
        await ctx.send(f"Created the role {role.mention}")

    @role.subcommand()
    @ipye.setup_options
    async def delete(
        self,
        ctx: ipy.CommandContext,
        role: Annotated[
            ipy.Role,
            ipye.EnhancedOption(ipy.Role, description="The role to be deleted"),
        ],
    ):
        """Request to delete a mentionable role"""
        if not is_joinable(role):
            await ctx.send(f"You cannot request to delete this role", ephemeral=True)
            return

        for user in await ctx.guild.get_all_members():
            if role.id in user.roles and user.id != ctx.author.id:
                await ctx.send(
                    f"There are 1 or more people still in this role", ephemeral=True
                )
                return

        await ctx.guild.delete_role(
            role, f"Deleted by {ctx.author.name} via bot commands"
        )
        await ctx.send(f"Role '{role.name}' has been deleted")

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
            await ctx.send("There are no new roles you can join", ephemeral=True)
            return

        role_dropdown = ipy.SelectMenu(
            custom_id=f"{ROLE_TOGGLE_PREFIX}join",
            placeholder="Join a mention role",
            max_values=len(options),
            options=options,
        )
        await ctx.send(components=role_dropdown, ephemeral=True)

    @role.subcommand()
    @ipye.setup_options
    async def leave(self, ctx: ipy.CommandContext):
        """Remove yourself from a mention role"""
        options = [
            ipy.SelectOption(label=role.name, value=role.name)
            for role in await ctx.guild.get_all_roles()
            if is_joinable(role) and role.id in ctx.author.roles
        ]
        if not options:
            await ctx.send("There are no roles you can leave", ephemeral=True)
            return

        role_dropdown = ipy.SelectMenu(
            custom_id=f"{ROLE_TOGGLE_PREFIX}leave",
            placeholder="Leave a mention role",
            max_values=len(options),
            options=options,
        )
        await ctx.send(components=role_dropdown, ephemeral=True)

    @ipy.extension_component(ROLE_TOGGLE_PREFIX, startswith=True)
    async def toggle_role(self, ctx: ipy.ComponentContext):
        """Callback after a selection is made on a join/leave dropdown"""
        role_names = ctx.data.values

        if not role_names:
            logger.warning(f"Toggle role callback called without role values...")
            await ctx.send(
                "Sorry, something went wrong. Try again later.", ephemeral=True
            )
            return

        user_is_joining = ctx.custom_id.lower().endswith("join")
        logger.info(
            f"Toggle role callback called with id {ctx.custom_id}. user_is_joining={user_is_joining}"
        )

        toggle_role = ctx.author.add_role if user_is_joining else ctx.author.remove_role

        invalid_roles = []
        toggled_roles = {}

        valid_roles = {
            r.name: r for r in await ctx.guild.get_all_roles() if is_joinable(r)
        }

        for role_name in role_names:
            if role_name not in valid_roles:
                logger.info(f"{role_name} is not a toggleable role. Skipping...")
                invalid_roles.append(role_name)
                continue

            if (valid_roles[role_name].id in ctx.author.roles) == user_is_joining:
                # To avoid re-calling discord APIs to join/eave roles the user is in
                logger.info(
                    f"{ctx.author.name} already had {role_name} set to {user_is_joining}. Skipping..."
                )
                toggled_roles[role_name] = None
                continue

            logger.info(f"{ctx.author.name} attempting to toggle {role_name}")
            toggled_roles[role_name] = toggle_role(
                valid_roles[role_name],
                ctx.guild_id,
                f"{ctx.author.name} toggled role via join/leave command",
            )

        await asyncio.gather(*(x for x in toggled_roles.values() if x is not None))

        if toggled_roles:
            await ctx.send(
                f"Successfully {'joined' if user_is_joining else 'left'} {', '.join(toggled_roles)}",
                ephemeral=True,
            )

        if invalid_roles:
            await ctx.send(
                f"Failed to {'join' if user_is_joining else 'leave'} {', '.join(invalid_roles)}.",
                ephemeral=True,
            )


def is_joinable(r: ipy.Role) -> bool:
    return r.mentionable and r.permissions == "0"


def setup(client: ipy.Client):
    RolesExtension(client)
