import logging
from typing import Annotated, Optional
import interactions as ipy
import interactions.ext.enhanced as ipye

from config import CONFIG

__all__ = ["setup", "RolesExtension"]

logger = logging.getLogger(__name__)

ipy.Option


class ChannelsExtension(ipy.Extension):
    def __init__(self, client: ipy.Client) -> None:
        self.client: ipy.Client = client

    @ipy.extension_command(scope=CONFIG.GUILD_ID)
    async def channel(self, _: ipy.CommandContext):
        pass

    @channel.subcommand()
    @ipye.setup_options
    async def create(
        self,
        ctx: ipy.CommandContext,
        name: Annotated[
            str, ipye.EnhancedOption(str, description="The name of the new channel")
        ],
        category: ipye.EnhancedOption(
            ipy.Channel,
            description="Optional channel category",
            channel_types=[ipy.ChannelType.GUILD_CATEGORY],
        ) = None,
    ):
        """Create a new text channel"""

        existing_channel = next(
            (
                c
                for c in await ctx.guild.get_all_channels()
                if c.type != ipy.ChannelType.GUILD_CATEGORY and c.name == name
            ),
            None,
        )
        if existing_channel:
            await ctx.send(f"{existing_channel.mention} already exists", ephemeral=True)
            return

        channel = await ctx.guild.create_channel(
            name,
            ipy.ChannelType.GUILD_TEXT,
            parent_id=category or ipy.MISSING,
            reason=f"Created by {ctx.author.name} via bot commands",
        )

        await ctx.send(f"{channel.mention} created successfully")


def setup(client: ipy.Client):
    ChannelsExtension(client)
