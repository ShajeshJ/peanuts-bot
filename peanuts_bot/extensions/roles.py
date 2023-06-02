import logging
import asyncio
from typing import Annotated
import interactions as ipy

from config import CONFIG
from peanuts_bot.errors import BotUsageError

__all__ = ["setup", "RolesExtension"]

logger = logging.getLogger(__name__)

ROLE_TOGGLE_PREFIX = "role_toggle_"
_JOINABLE_PERMISSION_SET: ipy.Permissions = ipy.Permissions.NONE


class RolesExtension(ipy.Extension):
    @ipy.slash_command(scopes=[CONFIG.GUILD_ID])
    async def role(self, _: ipy.SlashContext):
        pass

    @role.subcommand()
    async def create(
        self,
        ctx: ipy.SlashContext,
        name: Annotated[
            str, ipy.slash_str_option(required=True, description="Name of the new role")
        ],
    ):
        """Create a new mention role that others can join"""

        if any(r.name == name for r in ctx.guild.roles):
            raise BotUsageError(f"The role {name} already exists")

        role = await ctx.guild.create_role(
            name=name,
            mentionable=True,
            reason=f"Created by {ctx.author.username} via bot commands",
            permissions=_JOINABLE_PERMISSION_SET,
        )

        # TODO: A hack to get around a bug with `create_role`. Update this when
        # https://github.com/interactions-py/interactions.py/issues/1420 is fixed
        await role.edit(
            name=name,
            mentionable=True,
            permissions=_JOINABLE_PERMISSION_SET,
        )
        await ctx.send(f"Created new role {role.mention}")

    @role.subcommand()
    async def delete(
        self,
        ctx: ipy.SlashContext,
        role: Annotated[
            ipy.Role,
            ipy.slash_role_option(description="The role to be deleted", required=True),
        ],
    ):
        """Request to delete a mentionable role"""
        if not is_joinable(role):
            raise BotUsageError(f"You cannot request to delete this role")

        if any(m for m in role.members if m.id != ctx.author.id):
            raise BotUsageError(f"There are 1 or more people still in '{role.name}'")

        await role.delete(f"Deleted by {ctx.author.username} via bot commands")
        await ctx.send(f"Deleted role '{role.name}'")

    @role.subcommand()
    async def join(self, ctx: ipy.SlashContext):
        """Add yourself to a mention role"""
        options = [
            ipy.StringSelectOption(label=role.name, value=role.id)
            for role in ctx.guild.roles
            if is_joinable(role) and not ctx.author.has_role(role)
        ]
        if not options:
            raise BotUsageError("There are no new roles you can join")

        role_dropdown = ipy.StringSelectMenu(
            *options,
            custom_id=f"{ROLE_TOGGLE_PREFIX}join",
            placeholder="Join a mention role",
            max_values=len(options),
        )
        await ctx.send(components=role_dropdown, ephemeral=True)

    @role.subcommand()
    async def leave(self, ctx: ipy.SlashContext):
        """Remove yourself from a mention role"""
        options = [
            ipy.StringSelectOption(label=role.name, value=role.id)
            for role in ctx.guild.roles
            if is_joinable(role) and role.id in ctx.author.roles
        ]
        if not options:
            raise BotUsageError("There are no roles you can leave")

        role_dropdown = ipy.StringSelectMenu(
            *options,
            custom_id=f"{ROLE_TOGGLE_PREFIX}leave",
            placeholder="Leave a mention role",
            max_values=len(options),
        )
        await ctx.send(components=role_dropdown, ephemeral=True)

    # @ipy.extension_component(ROLE_TOGGLE_PREFIX, startswith=True)
    # async def toggle_role(self, ctx: ipy.ComponentContext):
    #     """Callback after a selection is made on a join/leave dropdown"""
    #     role_names = ctx.data.values

    #     user_is_joining = ctx.custom_id.lower().endswith("join")
    #     logger.info(
    #         f"Toggle role callback called with id {ctx.custom_id}. user_is_joining={user_is_joining}"
    #     )

    #     toggle_role = ctx.author.add_role if user_is_joining else ctx.author.remove_role

    #     invalid_roles = []
    #     toggled_roles = {}

    #     valid_roles = {
    #         r.name: r for r in await ctx.guild.get_all_roles() if is_joinable(r)
    #     }

    #     for role_name in role_names:
    #         if role_name not in valid_roles:
    #             logger.info(f"{role_name} is not a toggleable role. Skipping...")
    #             invalid_roles.append(role_name)
    #             continue

    #         if (valid_roles[role_name].id in ctx.author.roles) == user_is_joining:
    #             # To avoid re-calling discord APIs to join/eave roles the user is in
    #             logger.info(
    #                 f"{ctx.author.name} already had {role_name} set to {user_is_joining}. Skipping..."
    #             )
    #             toggled_roles[role_name] = None
    #             continue

    #         logger.info(f"{ctx.author.name} attempting to toggle {role_name}")
    #         toggled_roles[role_name] = toggle_role(
    #             valid_roles[role_name],
    #             ctx.guild_id,
    #             f"{ctx.author.name} toggled role via join/leave command",
    #         )

    #     await asyncio.gather(*(x for x in toggled_roles.values() if x is not None))

    #     if toggled_roles:
    #         await ctx.send(
    #             f"Successfully {'joined' if user_is_joining else 'left'} {', '.join(toggled_roles)}",
    #             ephemeral=True,
    #         )

    #     if invalid_roles:
    #         await ctx.send(
    #             f"Failed to {'join' if user_is_joining else 'leave'} {', '.join(invalid_roles)}.",
    #             ephemeral=True,
    #         )


def is_joinable(r: ipy.Role) -> bool:
    return r.mentionable and r.permissions == _JOINABLE_PERMISSION_SET
