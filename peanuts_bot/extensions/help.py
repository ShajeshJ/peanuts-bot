from dataclasses import dataclass, field
from enum import Enum
import logging

import discord
from discord import app_commands
from discord.ext import commands

from peanuts_bot.config import CONFIG
from peanuts_bot.errors import BotUsageError
from peanuts_bot.extensions.internals.protocols import HelpCmdProto

__all__ = ["HelpExtension"]

logger = logging.getLogger(__name__)


class HelpExtension(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    def get_help_color() -> discord.Color:
        return discord.Color.from_str("#2C3E50")

    @app_commands.command(name="help")
    async def help(self, interaction: discord.Interaction) -> None:
        """See help information for all commands"""

        if not isinstance(interaction.user, discord.Member):
            raise BotUsageError("this command is only available in guilds")

        skip_admin_help = not interaction.user.guild_permissions.administrator

        guild = discord.Object(CONFIG.GUILD_ID)
        all_commands = self.bot.tree.get_commands(guild=guild)

        pages: list[HelpPage] = []
        for cmd in all_commands:
            pages.extend(_pages_for_tree_command(cmd, ignore_admin=skip_admin_help))
        pages.sort(key=lambda p: p.sort_order)

        if not pages:
            await interaction.response.send_message(
                "No commands available.", ephemeral=True
            )
            return

        embeds = [p.to_embed() for p in pages]
        view = HelpPaginator(embeds)
        await interaction.response.send_message(
            embed=embeds[0], view=view, ephemeral=True
        )


class SortOrder(int, Enum):
    SLASH_CMD = 0
    CONTEXT_MENU = 8
    SLASH_ADMIN_CMD = 16


@dataclass
class HelpPage:
    title: str
    desc: str
    args: list[tuple[str, str]] = field(default_factory=list)
    color: discord.Color = field(default_factory=lambda: discord.Color(0))
    sort_order: SortOrder = SortOrder.SLASH_CMD

    def to_embed(self) -> discord.Embed:
        embed = discord.Embed(title=self.title, description=self.desc, color=self.color)
        for field_name, field_value in self.args:
            embed.add_field(name=field_name, value=field_value)
        return embed


class HelpPaginator(discord.ui.View):
    def __init__(self, pages: list[discord.Embed], *, timeout: float = 300) -> None:
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current = 0
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev_btn.disabled = self.current == 0
        self.next_btn.disabled = self.current == len(self.pages) - 1
        select: discord.ui.Item = self.page_select
        if isinstance(select, discord.ui.Select):
            select.options = [
                discord.SelectOption(
                    label=(p.title or f"Page {i + 1}")[:100],
                    value=str(i),
                    default=(i == self.current),
                )
                for i, p in enumerate(self.pages)
            ]

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.current = max(0, self.current - 1)
        self._update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current], view=self
        )

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.current = min(len(self.pages) - 1, self.current + 1)
        self._update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current], view=self
        )

    @discord.ui.select(placeholder="Jump to a command...")
    async def page_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        self.current = int(select.values[0])
        self._update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current], view=self
        )


def _get_color(
    cmd: app_commands.Command | app_commands.Group | app_commands.ContextMenu,
) -> discord.Color:
    binding = getattr(cmd, "binding", None) or getattr(
        getattr(cmd, "callback", None), "__self__", None
    )
    if binding and isinstance(binding, HelpCmdProto):
        return binding.get_help_color()
    return discord.Color(0)


def _requires_admin(
    cmd: app_commands.Command | app_commands.ContextMenu,
) -> bool:
    perms = getattr(cmd, "default_permissions", None)
    if (
        perms is None
        and isinstance(cmd, app_commands.Command)
        and cmd.parent is not None
    ):
        perms = cmd.parent.default_permissions
    return perms is not None and bool(perms.administrator)


def _pages_for_tree_command(
    cmd: app_commands.Command | app_commands.Group | app_commands.ContextMenu,
    *,
    ignore_admin: bool,
) -> list[HelpPage]:
    if isinstance(cmd, app_commands.Group):
        pages: list[HelpPage] = []
        for sub in cmd.commands:
            pages.extend(_pages_for_tree_command(sub, ignore_admin=ignore_admin))
        return pages

    if isinstance(cmd, app_commands.ContextMenu):
        type_label = (
            "messages" if cmd.type == discord.AppCommandType.message else "users"
        )
        return [
            HelpPage(
                title=cmd.name,
                desc=f"Available in right click context menus on {type_label}",
                color=_get_color(cmd),
                sort_order=SortOrder.CONTEXT_MENU,
            )
        ]

    is_admin_cmd = _requires_admin(cmd)
    if is_admin_cmd and ignore_admin:
        return []

    cmd_args: list[tuple[str, str]] = []
    for param in cmd.parameters:
        type_name = param.type.name.lower()
        if param.required:
            field_name = f"{param.name} (_{type_name}_)"
        else:
            field_name = f"{param.name} (_{type_name}_, optional)"
        cmd_args.append((field_name, param.description))

    return [
        HelpPage(
            title=f"/{cmd.qualified_name}",
            desc=f"```{cmd.description}```",
            args=cmd_args,
            color=_get_color(cmd),
            sort_order=SortOrder.SLASH_CMD
            if not is_admin_cmd
            else SortOrder.SLASH_ADMIN_CMD,
        )
    ]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpExtension(bot))
