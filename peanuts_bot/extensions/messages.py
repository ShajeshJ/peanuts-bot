import logging
from typing import Annotated
import interactions as ipy
import interactions.ext.enhanced as ipye

from config import CONFIG
from peanuts_bot.errors import BotUsageError
from peanuts_bot.libraries.discord_bot import get_discord_msg_urls

__all__ = ["setup", "MessagesExtension"]

logger = logging.getLogger(__name__)


class MessagesExtension(ipy.Extension):
    def __init__(self, client: ipy.Client) -> None:
        self.client: ipy.Client = client

    @ipy.extension_command(
        scope=CONFIG.GUILD_ID, default_member_permissions=ipy.Permissions.ADMINISTRATOR
    )
    @ipye.setup_options
    async def speak(
        self,
        ctx: ipy.CommandContext,
        message: Annotated[
            str,
            ipye.EnhancedOption(str, description="The message for the bot to repeat"),
        ],
    ):
        """[ADMIN-ONLY] Make the bot say something"""
        await ctx.send(message)

    @ipy.extension_command(
        scope=CONFIG.GUILD_ID, default_member_permissions=ipy.Permissions.ADMINISTRATOR
    )
    async def messages(self, _: ipy.CommandContext):
        pass

    @messages.subcommand()
    @ipye.setup_options
    async def delete(
        self,
        ctx: ipy.CommandContext,
        amount: Annotated[
            int,
            ipye.EnhancedOption(
                int,
                description="**Caution against > 100**. The number of messages to delete.",
                min_value=1,
            ),
        ] = 1,
    ):
        """[ADMIN-ONLY] Deletes the last X messages in the channel"""

        await ctx.defer(ephemeral=True)
        # TODO: Need to find out why bulk=True doesn't work
        msgs = await ctx.channel.purge(amount, bulk=False)
        await ctx.send(f"Deleted {len(msgs)} message(s)", ephemeral=True)

    @ipy.extension_command(scope=CONFIG.GUILD_ID)
    @ipye.setup_options
    async def quote(
        self,
        ctx: ipy.CommandContext,
        link: Annotated[
            str,
            ipye.EnhancedOption(str, description="The link to the message to quote"),
        ],
    ):
        """Quote a message"""

        try:
            message = await ipy.Message.get_from_url(link, self.client._http)
        except ipy.LibraryException as e:
            if e.code == 12:
                raise BotUsageError("Invalid message link") from e
            raise

        quote_as_embed = await self._create_quote_embed(message)
        if not quote_as_embed:
            raise BotUsageError("Unable to quote the given message link")

        await ctx.send(embeds=quote_as_embed)

    @ipy.extension_listener(name="on_message_create")
    async def auto_quote(self, msg: ipy.Message):
        """Automatically quote any messages that contain a discord message link"""

        if not msg.guild_id and msg.guild_id != CONFIG.GUILD_ID:
            return

        quote_as_embed = None

        for url in get_discord_msg_urls(msg.content):
            try:
                quoted_msg = await ipy.Message.get_from_url(url, self.client._http)
            except ipy.LibraryException:
                logger.debug(
                    "url regex found match but library get the message from the url",
                    exc_info=True,
                )
                continue

            if quote_as_embed := await self._create_quote_embed(quoted_msg):
                break

        if not quote_as_embed:
            return

        await msg.reply(embeds=quote_as_embed)

    async def _create_quote_embed(self, msg: ipy.Message) -> ipy.Embed | None:
        """Construct an embed quote from a message object"""

        embed = ipy.Embed()

        # Set author
        embed.set_author(
            name=msg.author.username,
            icon_url=msg.author.avatar_url,
        )

        # Add image from either attachments or other embeds on the message if possible
        for attached in msg.attachments:
            if (
                attached.content_type and attached.content_type.startswith("image/")
            ) or attached.url.endswith((".png", ".jpg", ".jpeg", ".gif")):
                embed.set_image(url=attached.url)
                break

        if not embed.image:
            embed_image_url = next((e.image.url for e in msg.embeds if e.image), None)
            if embed_image_url and embed_image_url:
                embed.set_image(url=embed_image_url)

        # Set quoted message content with a link to the original
        embed.description = msg.content
        if embed.description:
            embed.description += "\n\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\n"
        embed.description += f"[**View Original**]({str(msg.url)})"

        # Set footer with origin channel and message timestamp
        embed.set_footer(text=f"in #{(await msg.get_channel()).name}")
        embed.timestamp = msg.edited_timestamp or msg.timestamp

        return embed


def setup(client: ipy.Client):
    MessagesExtension(client)