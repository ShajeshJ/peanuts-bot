import logging
from typing import Annotated
import interactions as ipy
import interactions.ext.enhanced as ipye

from config import CONFIG


logger = logging.getLogger(__name__)


class EmojiExtensions(ipy.Extension):
    def __init__(self, client: ipy.Client) -> None:
        self.client: ipy.Client = client

    @ipy.extension_command(scope=CONFIG.GUILD_ID)
    @ipye.setup_options
    async def emoji(
        self,
        ctx: ipy.CommandContext,
        shortcut: Annotated[
            str, ipye.EnhancedOption(str, description="Shortcut for the emoji")
        ],
        emoji: ipye.EnhancedOption(ipy.Attachment, description="Image of the emoji"),
    ):
        """Request a new Emoji to be added"""

        emoji: ipy.Attachment = emoji

        admin_user = await ctx.guild.get_member(CONFIG.ADMIN_USER_ID)

        logger.info(f"File type {emoji.content_type}")

        await admin_user.send(
            f"{ctx.author.name} requested to create this emoji ({emoji.url}) with the shortcut {shortcut}",
            # attachments=[emoji],
        )


def setup(client: ipy.Client):
    EmojiExtensions(client)
