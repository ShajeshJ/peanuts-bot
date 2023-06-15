from dataclasses import dataclass, field
from enum import Enum
import logging
import interactions as ipy
from interactions.ext.paginators import Paginator

from config import CONFIG
from peanuts_bot.errors import BotUsageError
from peanuts_bot.extensions.internals.protocols import HelpCmdProto
from peanuts_bot.libraries.types_ext import get_annotated_subtype

__all__ = ["HelpExtensions"]

logger = logging.getLogger(__name__)


class HelpExtensions(ipy.Extension):
    @staticmethod
    def get_help_color() -> ipy.Color:
        return ipy.FlatUIColors.PETERRIVER

    @ipy.slash_command(scopes=[CONFIG.GUILD_ID])
    async def help(self, ctx: ipy.SlashContext):
        """See help information for all commands"""

        if not isinstance(ctx.author, ipy.Member):
            raise BotUsageError("this command is only available in guilds")

        skip_admin_help = not ctx.author.has_permission(ipy.Permissions.ADMINISTRATOR)

        help_page_gen = (
            HelpPage.from_command(c, ignore_admin=skip_admin_help)
            for c in self.bot.application_commands
        )
        pages = [page for page in help_page_gen if page is not None]
        pages.sort(key=lambda p: p.sort_order)

        help_dialog = Paginator.create_from_embeds(
            self.bot, *(p.to_embed() for p in pages), timeout=300
        )
        help_dialog.show_select_menu = True
        await help_dialog.send(ctx)


def get_slash_cmd_desc(c: ipy.SlashCommand) -> str | None:
    default_desc = "No Description Set"

    if str(c.description) != default_desc:
        return str(c.description)
    elif str(c.sub_cmd_description) != default_desc:
        return str(c.sub_cmd_description)
    else:
        return None  # a parent command with no use


def requires_admin(c: ipy.InteractionCommand) -> bool:
    return bool(
        c.default_member_permissions is not None
        and c.default_member_permissions & ipy.Permissions.ADMINISTRATOR
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
    color: ipy.Color = field(default_factory=ipy.Color)
    sort_order: SortOrder = SortOrder.SLASH_CMD

    def to_embed(self) -> ipy.Embed:
        embed = ipy.Embed(title=self.title, description=self.desc, color=self.color)
        for field_name, field_value in self.args:
            embed.add_field(name=field_name, value=field_value)
        return embed

    @staticmethod
    def from_command(
        c: ipy.InteractionCommand, /, *, ignore_admin=True
    ) -> "HelpPage | None":
        color = (
            c.extension.__class__.get_help_color()
            if c.extension and isinstance(c.extension, HelpCmdProto)
            else ipy.Color()
        )

        if isinstance(c, ipy.ContextMenu):
            return HelpPage(
                title=f"{c.resolved_name}",
                desc=f"Available in right click context menus on {c.type.name.lower()}s",
                color=color,
                sort_order=SortOrder.CONTEXT_MENU,
            )

        elif isinstance(c, ipy.SlashCommand):
            is_admin_cmd = requires_admin(c)
            if is_admin_cmd and ignore_admin:
                return None

            desc = get_slash_cmd_desc(c)
            if desc is None:
                return None

            cmd_args: list[tuple[str, str]] = []

            for param_name, param_config in c.parameters.items():
                _, metadata = get_annotated_subtype(param_config.type)
                if not metadata:
                    logger.warn(f"missing param annotations for {c.resolved_name}")
                    continue

                param: ipy.SlashCommandOption = metadata[0]

                field_name = f"{param_name} (_{param.type.name.lower()}_)"
                if not param.required:
                    field_name = f"{field_name[:-1]}, optional)"

                cmd_args.append((field_name, str(param.description)))

            return HelpPage(
                title=f"/{c.resolved_name}",
                desc=f"```{desc}```",
                args=cmd_args,
                color=color,
                sort_order=(
                    SortOrder.SLASH_CMD
                    if not is_admin_cmd
                    else SortOrder.SLASH_ADMIN_CMD
                ),
            )

        raise ValueError(f"unknown command {c.resolved_name}")
