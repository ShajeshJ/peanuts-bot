import functools
import logging
from typing import Annotated
import interactions as ipy

from peanuts_bot.config import CONFIG
from peanuts_bot.errors import BotUsageError

__all__ = ["ChannelExtension"]

logger = logging.getLogger(__name__)


class ChannelExtension(ipy.Extension):
    @staticmethod
    def get_help_color() -> ipy.Color:
        return ipy.FlatUIColors.PETERRIVER

    @ipy.slash_command(scopes=[CONFIG.GUILD_ID])
    async def channel(self, _: ipy.SlashContext):
        pass

    @channel.subcommand()
    async def create(
        self,
        ctx: ipy.SlashContext,
        name: Annotated[
            str,
            ipy.slash_str_option(
                description="The name of the new channel", required=True
            ),
        ],
        category: Annotated[
            ipy.GuildCategory | None,
            ipy.slash_channel_option(
                description="Category to nest the channel under",
                channel_types=[ipy.ChannelType.GUILD_CATEGORY],
            ),
        ] = None,
    ):
        """Create a new text channel"""

        if not ctx.guild:
            raise BotUsageError("This command can only be used in a server")

        existing_channel = next(
            (
                c
                for c in await ctx.guild.fetch_channels()
                if c.type != ipy.ChannelType.GUILD_CATEGORY and c.name == name
            ),
            None,
        )
        if existing_channel:
            raise BotUsageError(f"{existing_channel.mention} already exists")

        create_channel = functools.partial(
            ctx.guild.create_channel,
            channel_type=ipy.ChannelType.GUILD_TEXT,
            name=name,
            reason=f"Created by {ctx.author.display_name} via bot commands",
        )

        if category:
            channel = await create_channel(category=category)
        else:
            channel = await create_channel()

        await ctx.send(f"Created new channel {channel.mention}")
