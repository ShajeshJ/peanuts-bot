import logging
from typing import Annotated, Callable, NamedTuple
from collections.abc import Iterator, AsyncIterator
import interactions as ipy

from config import CONFIG
from peanuts_bot.errors import BotUsageError

__all__ = ["setup", "RolesExtension"]

logger = logging.getLogger(__name__)

ROLE_JOIN_ID = f"role_join"
ROLE_LEAVE_ID = f"role_leave"

_JOINABLE_PERMISSION_SET: ipy.Permissions = ipy.Permissions.NONE


class RolesExtension(ipy.Extension):
    @ipy.slash_command(scopes=[CONFIG.GUILD_ID], dm_permission=False)
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
            ipy.StringSelectOption(label=role.name, value=get_role_option_value(role))
            for role in ctx.guild.roles
            if is_joinable(role) and not ctx.author.has_role(role)
        ]
        if not options:
            raise BotUsageError("There are no new roles you can join")

        role_dropdown = ipy.StringSelectMenu(
            *options,
            custom_id=ROLE_JOIN_ID,
            placeholder="Join a mention role",
            max_values=len(options),
        )
        await ctx.send(components=role_dropdown, ephemeral=True)

    @ipy.component_callback(ROLE_JOIN_ID)
    async def join_selection(self, ctx: ipy.ComponentContext):
        """Callback after a selection is made on a join dropdown"""

        invalid_roles = []
        joined_roles = []
        role_gen = get_valid_roles(
            selected_roles=(split_role_option_value(v) for v in ctx.values),
            ctx=ctx,
            should_skip=lambda ctx, r: ctx.author.has_role(r),
            invalid_role_callback=invalid_roles.append,
        )

        async for role in role_gen:
            logger.debug(f"{ctx.author.display_name} attempting to join {role.name}")
            joined_roles.append(role.name)
            await ctx.author.add_role(
                role, f"{ctx.author.display_name} joined role via join command"
            )

        if joined_roles:
            await ctx.send(
                f"Successfully joined {', '.join(joined_roles)}", ephemeral=True
            )

        if invalid_roles:
            await ctx.send(
                f"Failed to join {', '.join(invalid_roles)}.", ephemeral=True
            )

    @role.subcommand()
    async def leave(self, ctx: ipy.SlashContext):
        """Remove yourself from a mention role"""
        options = [
            ipy.StringSelectOption(label=role.name, value=get_role_option_value(role))
            for role in ctx.guild.roles
            if is_joinable(role) and role.id in ctx.author.roles
        ]
        if not options:
            raise BotUsageError("There are no roles you can leave")

        role_dropdown = ipy.StringSelectMenu(
            *options,
            custom_id=ROLE_LEAVE_ID,
            placeholder="Leave a mention role",
            max_values=len(options),
        )
        await ctx.send(components=role_dropdown, ephemeral=True)

    @ipy.component_callback(ROLE_LEAVE_ID)
    async def leave_selection(self, ctx: ipy.ComponentContext):
        """Callback after a selection is made on a leave dropdown"""

        invalid_roles = []
        left_roles = []
        role_gen = get_valid_roles(
            selected_roles=(split_role_option_value(v) for v in ctx.values),
            ctx=ctx,
            should_skip=lambda ctx, r: not ctx.author.has_role(r),
            invalid_role_callback=invalid_roles.append,
        )

        async for role in role_gen:
            logger.debug(f"{ctx.author.display_name} attempting to leave {role.name}")
            left_roles.append(role.name)
            await ctx.author.remove_role(
                role, f"{ctx.author.display_name} left role via leave command"
            )

        if left_roles:
            await ctx.send(f"Successfully left {', '.join(left_roles)}", ephemeral=True)

        if invalid_roles:
            await ctx.send(
                f"Failed to leave {', '.join(invalid_roles)}.", ephemeral=True
            )


class RoleOptionTuple(NamedTuple):
    id: ipy.Snowflake
    name: str


async def get_valid_roles(
    selected_roles: Iterator[RoleOptionTuple],
    ctx: ipy.ComponentContext,
    should_skip: Callable[[ipy.ComponentContext, ipy.Role], bool],
    invalid_role_callback: Callable[[str], None],
) -> AsyncIterator[ipy.Role]:
    """
    Returns an iterator that yields roles to join/leave.

    :param selected_roles: The roles selected by the user
    :param ctx: The context of the interaction
    :param should_skip: A function that returns True if the role should be skipped
    :param invalid_role_callback: A function that is called when a role is invalid
    :return: An iterator that yields roles to join/leave
    """

    if not ctx.guild or not isinstance(ctx.author, ipy.Member):
        raise ValueError("ctx must be in a guild context, where author is a member")

    for role_id, role_name in selected_roles:
        role = await ctx.guild.fetch_role(role_id)
        if not role:
            logger.debug(f"{role_name} does not exist. Skipping...")
            invalid_role_callback(role_name)
            continue

        if should_skip(ctx, role):
            logger.debug(
                f"{ctx.author.display_name} met skip condition for {role_name}. Skipping..."
            )
            continue

        if not is_joinable(role):
            logger.debug(f"{role_name} is not a joinable role. Skipping...")
            invalid_role_callback(role_name)
            continue

        yield role


def get_role_option_value(role: ipy.Role) -> str:
    return f"{role.id}|{role.name}"


def split_role_option_value(value: str) -> RoleOptionTuple:
    r_id, r_name = value.split("|")
    return RoleOptionTuple(ipy.Snowflake(r_id), r_name)


def is_joinable(r: ipy.Role) -> bool:
    return r.mentionable and r.permissions == _JOINABLE_PERMISSION_SET
