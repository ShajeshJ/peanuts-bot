from dataclasses import dataclass, field
from enum import Enum
import logging
import typing
import interactions as ipy
from interactions.ext.paginators import Paginator

from config import CONFIG
from peanuts_bot.errors import BotUsageError

__all__ = ["HelpExtensions"]

logger = logging.getLogger(__name__)


class HelpExtensions(ipy.Extension):
    @ipy.slash_command(scopes=[CONFIG.GUILD_ID])
    async def help(self, ctx: ipy.SlashContext):
        """See help information for all commands"""

        if not isinstance(ctx.author, ipy.Member):
            raise BotUsageError("this command is only available in guilds")

        help_page_gen = (
            HelpPage.from_command(
                c,
                ignore_admin=not ctx.author.has_permission(
                    ipy.Permissions.ADMINISTRATOR
                ),
            )
            for c in self.bot.application_commands
        )
        pages = [page for page in help_page_gen if page is not None]
        pages.sort(key=lambda p: p.sort_priority)

        help_dialog = Paginator.create_from_embeds(
            self.bot, *(p.to_embed() for p in pages), timeout=300
        )
        help_dialog.show_select_menu = True
        await help_dialog.send(ctx)


def desc_is_missing(d: ipy.LocalisedDesc | str) -> bool:
    return str(d) == "No Description Set"


class SortPriority(int, Enum):
    SLASH_CMD = 0
    SLASH_ADMIN_CMD = 8
    CONTEXT_MENU = 16


@dataclass
class HelpPage:
    title: str
    desc: str
    args: list[tuple[str, str]] = field(default_factory=list)
    sort_priority: SortPriority = SortPriority.SLASH_CMD

    def to_embed(self) -> ipy.Embed:
        embed = ipy.Embed(title=self.title, description=self.desc)
        for field_name, field_value in self.args:
            embed.add_field(name=field_name, value=field_value)
        return embed

    @staticmethod
    def from_command(
        c: ipy.InteractionCommand, /, *, ignore_admin=True
    ) -> "HelpPage | None":
        if isinstance(c, ipy.ContextMenu):
            return HelpPage(
                title=f"{c.resolved_name}",
                desc=f"Available in right click context menus on {c.type.name.lower()}s",
                sort_priority=SortPriority.CONTEXT_MENU,
            )

        elif isinstance(c, ipy.SlashCommand):
            is_admin_cmd = bool(
                c.default_member_permissions is not None
                and c.default_member_permissions & ipy.Permissions.ADMINISTRATOR
            )
            if is_admin_cmd and ignore_admin:
                return None

            if not desc_is_missing(c.description):
                desc = c.description
            elif not desc_is_missing(c.sub_cmd_description):
                desc = c.sub_cmd_description
            else:
                return None  # a parent command with no use; skip

            title = f"/{c.resolved_name}"
            desc = f"```{desc}```"

            args: list[tuple[str, str]] = []

            for param_name, param_config in c.parameters.items():
                if typing.get_origin(param_config.type) is not typing.Annotated:
                    logger.warning(
                        f"unknown type for option in command {c.resolved_name}"
                    )
                    continue

                annotation_args = typing.get_args(param_config.type)
                param: ipy.SlashCommandOption = annotation_args[1]

                field_name = f"{param_name} ({param.type.name.lower()})"
                if not param.required:
                    field_name = f"_{field_name[:-1]} | optional)_"

                args.append((field_name, f"{param.description}"))

            return HelpPage(
                title=title,
                desc=desc,
                args=args,
                sort_priority=(
                    SortPriority.SLASH_CMD
                    if not is_admin_cmd
                    else SortPriority.SLASH_ADMIN_CMD
                ),
            )

        raise ValueError(f"unknown command {c.resolved_name}")
