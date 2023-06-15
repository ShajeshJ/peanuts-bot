import logging
from typing import Annotated
import interactions as ipy

from config import CONFIG
from peanuts_bot.errors import BotUsageError

__all__ = ["ChannelExtension"]

logger = logging.getLogger(__name__)


class ChannelExtension(ipy.Extension):
    @staticmethod
    def get_help_color() -> ipy.Color:
        return ipy.FlatUIColors.MIDNIGHTBLUE

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

        logger.info(category)

        channel = await ctx.guild.create_channel(
            channel_type=ipy.ChannelType.GUILD_TEXT,
            name=name,
            category=category,
            reason=f"Created by {ctx.author.display_name} via bot commands",
        )

        await ctx.send(f"Created new channel {channel.mention}")
