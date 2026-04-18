import logging
from collections.abc import AsyncGenerator, Callable, Iterator
from typing import NamedTuple

import discord
from discord import app_commands
from discord.ext import commands

from peanuts_bot.errors import BotUsageError, handle_interaction_error

__all__ = ["RoleExtension"]

logger = logging.getLogger(__name__)

ROLE_JOIN_ID = "role_join"
ROLE_LEAVE_ID = "role_leave"

_role_group = app_commands.Group(name="role", description="Role management commands")


class RoleOptionTuple(NamedTuple):
    id: int
    name: str


def _is_joinable(r: discord.Role) -> bool:
    return r.mentionable and r.permissions == discord.Permissions.none()


def _get_role_option_value(role: discord.Role) -> str:
    return f"{role.id}|{role.name}"


def _split_role_option_value(value: str) -> RoleOptionTuple:
    r_id, r_name = value.split("|")
    return RoleOptionTuple(int(r_id), r_name)


async def _get_valid_roles(
    selected_roles: Iterator[RoleOptionTuple],
    guild: discord.Guild,
    member: discord.Member,
    should_skip: Callable[[discord.Member, discord.Role], bool],
    invalid_role_callback: Callable[[str], None],
) -> AsyncGenerator[discord.Role, None]:
    for role_id, role_name in selected_roles:
        role = guild.get_role(role_id)
        if not role:
            logger.debug(f"{role_name} does not exist. Skipping...")
            invalid_role_callback(role_name)
            continue

        if should_skip(member, role):
            logger.debug(
                f"{member.display_name} met skip condition for {role_name}. Skipping..."
            )
            continue

        if not _is_joinable(role):
            logger.debug(f"{role_name} is not a joinable role. Skipping...")
            invalid_role_callback(role_name)
            continue

        yield role


class RoleJoinView(discord.ui.View):
    def __init__(self, options: list[discord.SelectOption] | None = None) -> None:
        super().__init__(timeout=None)
        if options is not None:
            for child in self.children:
                if isinstance(child, discord.ui.Select):
                    child.options = options
                    child.max_values = len(options)
                    break

    @discord.ui.select(
        custom_id=ROLE_JOIN_ID,
        placeholder="Join a mention role",
        min_values=1,
        max_values=25,
    )
    async def join_selection(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            raise BotUsageError("This command can only be used in a server")

        await interaction.response.defer(ephemeral=True)
        member = interaction.user

        invalid_roles: list[str] = []
        joined_roles: list[str] = []

        async for role in _get_valid_roles(
            selected_roles=(_split_role_option_value(v) for v in select.values),
            guild=interaction.guild,
            member=member,
            should_skip=lambda m, r: r in m.roles,
            invalid_role_callback=invalid_roles.append,
        ):
            logger.debug(f"{member.display_name} attempting to join {role.name}")
            joined_roles.append(role.name)
            await member.add_roles(
                role, reason=f"{member.display_name} joined role via join command"
            )

        parts = []
        if joined_roles:
            parts.append(f"Successfully joined {', '.join(joined_roles)}")
        if invalid_roles:
            parts.append(f"Failed to join {', '.join(invalid_roles)}.")
        if not parts:
            parts.append("No changes were made.")

        await interaction.followup.send("\n".join(parts), ephemeral=True)

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        await handle_interaction_error(interaction, error)


class RoleLeaveView(discord.ui.View):
    def __init__(self, options: list[discord.SelectOption] | None = None) -> None:
        super().__init__(timeout=None)
        if options is not None:
            for child in self.children:
                if isinstance(child, discord.ui.Select):
                    child.options = options
                    child.max_values = len(options)
                    break

    @discord.ui.select(
        custom_id=ROLE_LEAVE_ID,
        placeholder="Leave a mention role",
        min_values=1,
        max_values=25,
    )
    async def leave_selection(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            raise BotUsageError("This command can only be used in a server")

        await interaction.response.defer(ephemeral=True)
        member = interaction.user

        invalid_roles: list[str] = []
        left_roles: list[str] = []

        async for role in _get_valid_roles(
            selected_roles=(_split_role_option_value(v) for v in select.values),
            guild=interaction.guild,
            member=member,
            should_skip=lambda m, r: r not in m.roles,
            invalid_role_callback=invalid_roles.append,
        ):
            logger.debug(f"{member.display_name} attempting to leave {role.name}")
            left_roles.append(role.name)
            await member.remove_roles(
                role, reason=f"{member.display_name} left role via leave command"
            )

        parts = []
        if left_roles:
            parts.append(f"Successfully left {', '.join(left_roles)}")
        if invalid_roles:
            parts.append(f"Failed to leave {', '.join(invalid_roles)}.")
        if not parts:
            parts.append("No changes were made.")

        await interaction.followup.send("\n".join(parts), ephemeral=True)

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        await handle_interaction_error(interaction, error)


@_role_group.command(name="create")
@app_commands.describe(name="Name of the new role")
async def _role_create(interaction: discord.Interaction, name: str) -> None:
    """Create a new mention role that others can join"""
    if not interaction.guild:
        raise BotUsageError("This command can only be used in a server")

    if any(r.name == name for r in interaction.guild.roles):
        raise BotUsageError(f"The role {name} already exists")

    role = await interaction.guild.create_role(
        name=name,
        mentionable=True,
        reason=f"Created by {interaction.user.display_name} via bot commands",
        permissions=discord.Permissions.none(),
    )
    await interaction.response.send_message(f"Created new role {role.mention}")


@_role_group.command(name="delete")
@app_commands.describe(role="The role to be deleted")
async def _role_delete(interaction: discord.Interaction, role: discord.Role) -> None:
    """Request to delete a mentionable role"""
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        raise BotUsageError("This command can only be used in a server")

    if not _is_joinable(role):
        raise BotUsageError("You cannot request to delete this role")

    if any(m for m in role.members if m.id != interaction.user.id):
        raise BotUsageError(f"There are 1 or more people still in '{role.name}'")

    await role.delete(
        reason=f"Deleted by {interaction.user.display_name} via bot commands"
    )
    await interaction.response.send_message(f"Deleted role '{role.name}'")


@_role_group.command(name="join")
async def _role_join(interaction: discord.Interaction) -> None:
    """Add yourself to a mention role"""
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        raise BotUsageError("This command can only be used in a server")

    member = interaction.user
    options = [
        discord.SelectOption(label=role.name, value=_get_role_option_value(role))
        for role in interaction.guild.roles
        if _is_joinable(role) and role not in member.roles
    ]
    if not options:
        raise BotUsageError("There are no new roles you can join")

    view = RoleJoinView(options=options)
    await interaction.response.send_message(view=view, ephemeral=True)


@_role_group.command(name="leave")
async def _role_leave(interaction: discord.Interaction) -> None:
    """Remove yourself from a mention role"""
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        raise BotUsageError("This command can only be used in a server")

    member = interaction.user
    options = [
        discord.SelectOption(label=role.name, value=_get_role_option_value(role))
        for role in interaction.guild.roles
        if _is_joinable(role) and role in member.roles
    ]
    if not options:
        raise BotUsageError("There are no roles you can leave")

    view = RoleLeaveView(options=options)
    await interaction.response.send_message(view=view, ephemeral=True)


class RoleExtension(commands.Cog):
    @staticmethod
    def get_help_color() -> discord.Color:
        return discord.Color.from_str("#E74C3C")


async def setup(bot: commands.Bot) -> None:
    bot.tree.add_command(_role_group)
    bot.add_view(RoleJoinView())
    bot.add_view(RoleLeaveView())
    await bot.add_cog(RoleExtension())
