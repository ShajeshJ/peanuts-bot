import asyncio
from dataclasses import dataclass
import logging
import traceback
import aiohttp
import re
from typing import Annotated
import interactions as ipy

from config import CONFIG
from peanuts_bot.errors import BotUsageError, SOMETHING_WRONG
from peanuts_bot.libraries.discord_bot import disable_all_components
from peanuts_bot.libraries.image import (
    MAX_EMOJI_FILE_SIZE,
    ImageType,
    is_image,
    get_image_url,
    get_image_metadata,
)

__all__ = ["EmojiExtensions"]

logger = logging.getLogger(__name__)

APPROVE_EMOJI_BTN = "approve_emoji_btn"
REJECT_EMOJI_BTN = "deny_emoji_btn"
SHORTCUT_MODAL_PREFIX = "shortcut_modal_"
SHORTCUT_TEXT_PREFIX = "shortcut_value_"
REJECT_EMOJI_MODAL = "reject_emoji_modal"


@dataclass
class EmojiRequest:
    """
    Holds the contextual information for a given Emoji Request

    Attributes
    """

    shortcut: str | None
    url: str
    file_type: ImageType
    file_len: int
    requester_id: int
    channel_id: int

    def to_approval_msg(self) -> str:
        return (
            "new emoji request:\n"
            f"> shortcut: {self.shortcut}\n"
            f"> url: {self.url}\n"
            f"> requester_id: {self.requester_id}\n"
            f"> channel_id: {self.channel_id}"
        )

    @staticmethod
    def from_approval_msg(msg: str) -> "EmojiRequest":
        """
        Creates an EmojiRequest from a message created by `EmojiRequest.to_approval_msg()`

        :param msg: The message to parse
        :return: The EmojiRequest parsed from the message
        """
        try:
            shortcut = re.search(r"> shortcut: (.*)", msg).group(1)
            url = re.search(r"> url: (.*)", msg).group(1)
            requester_id = int(re.search(r"> requester_id: (.*)", msg).group(1))
            channel_id = int(re.search(r"> channel_id: (.*)", msg).group(1))
        except (AttributeError, TypeError, ValueError) as e:
            raise ValueError("unable to parse message as an emoji request") from e

        return EmojiRequest(
            shortcut=shortcut,
            url=url,
            file_type=ImageType.PNG,
            file_len=0,
            requester_id=requester_id,
            channel_id=channel_id,
        )


class EmojiExtensions(ipy.Extension):
    @ipy.slash_command(scopes=[CONFIG.GUILD_ID])
    async def emoji(
        self,
        ctx: ipy.SlashContext,
        shortcut: Annotated[
            str,
            ipy.slash_str_option(description="Shortcut for the emoji", required=True),
        ],
        emoji: Annotated[
            ipy.Attachment,
            ipy.slash_attachment_option(
                description="Image of the emoji", required=True
            ),
        ],
    ):
        """Request a new Emoji to be added"""

        if not is_image(emoji):
            raise BotUsageError(
                f"Not a valid file. Emoji images must be png, jpeg, or gif files."
            )

        url = get_image_url(emoji)
        content_type, content_length = await get_image_metadata(url)

        req = EmojiRequest(
            shortcut=shortcut,
            url=url,
            file_type=content_type,
            file_len=content_length,
            requester_id=ctx.author.id,
            channel_id=ctx.channel.id,
        )

        await _request_emoji(req, ctx)
        await ctx.send("Emoji request sent", ephemeral=True)

    @ipy.message_context_menu(name="Convert to Emoji", scopes=[CONFIG.GUILD_ID])
    async def emoji_from_attachment(self, ctx: ipy.ContextMenuContext):
        """Request to convert an attached image to an emoji"""

        if not isinstance(ctx.target, ipy.Message):
            raise TypeError("Message command's target must be a message")

        images = get_images_from_msg(ctx.target)

        text_fields = (
            ipy.InputText(
                custom_id=f"{SHORTCUT_TEXT_PREFIX}{i}",
                label=f"Emoji name to give to image {i+1}",
                style=ipy.TextStyles.SHORT,
                placeholder="Leave blank to skip this image",
                required=False,
            )
            for i in range(len(images))
        )
        modal = ipy.Modal(
            *text_fields,
            custom_id=f"{SHORTCUT_MODAL_PREFIX}{ctx.target_id}",
            title="Emoji Names",
        )
        await ctx.send_modal(modal)

    @ipy.modal_callback(re.compile(f"{SHORTCUT_MODAL_PREFIX}.*"))
    async def emoji_from_attachment_modal(self, ctx: ipy.ModalContext, **_):
        """Callback after user filled out modal triggered by `emoji_from_attachment`"""

        message_id = int(ctx.custom_id.replace(SHORTCUT_MODAL_PREFIX, ""))
        msg = await ctx.channel.fetch_message(message_id)
        if not msg:
            raise BotUsageError("Message has been deleted")
        images = get_images_from_msg(msg)

        emoji_requests = []

        for field_id, shortcut in ctx.responses.items():
            if not shortcut:
                continue

            index = int(field_id.replace(SHORTCUT_TEXT_PREFIX, ""))
            url = get_image_url(images[int(index)])
            content_type, content_length = await get_image_metadata(url)

            req = EmojiRequest(
                shortcut=shortcut,
                url=url,
                file_type=content_type,
                file_len=content_length,
                requester_id=ctx.author.id,
                channel_id=ctx.channel_id,
            )

            emoji_requests.append(_request_emoji(req, ctx))

        if not emoji_requests:
            await ctx.send("No emoji requests sent", ephemeral=True)
            return

        errors = [
            e
            for e in await asyncio.gather(*emoji_requests, return_exceptions=True)
            if isinstance(e, Exception)
        ]

        if not errors:
            await ctx.send("Emoji requests sent", ephemeral=True)
            return

        system_errors = [e for e in errors if not isinstance(e, BotUsageError)]

        if system_errors:
            logger.warning("Unexpected errors occurred in 1 or more emoji requests")

        for e in system_errors:
            logger.debug(
                f"\nEmoji request error:\n{''.join(traceback.format_exception(e))}"
            )

        error_strs = [
            f"\n- {str(e) if isinstance(e, BotUsageError) else SOMETHING_WRONG}"
            for e in errors
        ]
        await ctx.send(
            f"The following errors occurred: {''.join(error_strs)}", ephemeral=True
        )

    @ipy.component_callback(APPROVE_EMOJI_BTN)
    async def approve_emoji(self, ctx: ipy.ComponentContext):
        """Callback of an admin approving an emoji"""

        disabled_btns = disable_all_components(ctx.message.components)

        try:
            emoji_request = EmojiRequest.from_approval_msg(ctx.message.content)
        except ValueError as e:
            await ctx.message.edit(components=disabled_btns)
            raise BotUsageError("invalid emoji request message") from e

        # user and guild are not likely to go stale, so only force fetch channel
        channel = await self.bot.fetch_channel(emoji_request.channel_id, force=True)
        requester = await self.bot.fetch_member(
            emoji_request.requester_id, CONFIG.GUILD_ID
        )
        guild = await self.bot.fetch_guild(CONFIG.GUILD_ID)

        async with aiohttp.request("GET", emoji_request.url) as res:
            emoji = await guild.create_custom_emoji(
                emoji_request.shortcut,
                await res.content.read(),
                reason=f"Created by {requester.username} via bot comands",
            )
            await channel.send(f"{requester.mention} emoji {emoji} was created")

        await ctx.message.edit(components=disabled_btns)
        await ctx.send(f"approved emoji {emoji_request.shortcut}", ephemeral=True)

    @ipy.component_callback(REJECT_EMOJI_BTN)
    async def reject_emoji(self, ctx: ipy.ComponentContext):
        """Callback of an admin rejecting an emoji"""

        await ctx.send_modal(
            ipy.Modal(
                ipy.InputText(
                    custom_id="emoji_reject_reason",
                    label="Rejection Reason",
                    style=ipy.TextStyles.PARAGRAPH,
                    required=True,
                    placeholder="Emoji is weirdly sized.",
                    min_length=1,
                ),
                custom_id=REJECT_EMOJI_MODAL,
                title="Reject Emoji",
            )
        )

    @ipy.modal_callback(REJECT_EMOJI_MODAL)
    async def reject_emoji_modal(self, ctx: ipy.ModalContext, emoji_reject_reason: str):
        """Callback after admin filled out error reason for an emoji rejection"""

        disabled_btns = disable_all_components(ctx.message.components)

        try:
            emoji_request = EmojiRequest.from_approval_msg(ctx.message.content)
        except ValueError as e:
            await ctx.message.edit(components=disabled_btns)
            raise BotUsageError("invalid emoji request message") from e

        # requester is not likely to go stale, so only force fetch channel
        channel = await self.bot.fetch_channel(emoji_request.channel_id, force=True)
        requester = await self.bot.fetch_member(
            emoji_request.requester_id, CONFIG.GUILD_ID
        )

        await channel.send(
            f'{requester.mention} your emoji "{emoji_request.shortcut}" was rejected with reason:\n> {emoji_reject_reason}'
        )
        await ctx.send(f"rejected emoji {emoji_request.shortcut}", ephemeral=True)

        await ctx.message.edit(components=disabled_btns)


async def _request_emoji(req: EmojiRequest, ctx: ipy.SlashContext | ipy.ModalContext):
    """
    Sends a emoji creation request to the guild's Admin User

    :param req: The emoji request to be made
    :param ctx: The current command context

    :return: If the emoji could not be added, the string returned is the rejection reason.
    """
    logger.debug(f"File type: {req.file_type}")
    if not is_valid_emoji_type(req.file_type):
        raise BotUsageError(
            f"File for '{req.shortcut}' is not valid. Emoji images must be png, jpeg, or gif files."
        )

    logger.debug(f"File size: {req.file_len}")
    if req.file_len > MAX_EMOJI_FILE_SIZE:
        raise BotUsageError(
            f"File for '{req.shortcut}' is too large. Emoji images must be < {MAX_EMOJI_FILE_SIZE}"
        )

    if not req.shortcut or not is_valid_shortcut(req.shortcut):
        raise BotUsageError(
            f"{req.shortcut} is not a valid shortcut. Emoji Shortcuts must be alphanumeric or underscore characters only."
        )

    yes_btn = ipy.Button(
        label="Approve", style=ipy.ButtonStyle.SUCCESS, custom_id=APPROVE_EMOJI_BTN
    )

    no_btn = ipy.Button(
        label="Deny",
        style=ipy.ButtonStyle.DANGER,
        custom_id=REJECT_EMOJI_BTN,
    )

    admin_user = await ctx.bot.fetch_user(CONFIG.ADMIN_USER_ID)
    await admin_user.send(req.to_approval_msg(), components=[yes_btn, no_btn])


def is_valid_emoji_type(_type: ImageType) -> bool:
    return _type in [ImageType.JPEG, ImageType.PNG, ImageType.GIF]


def is_valid_shortcut(shortcut: str) -> bool:
    """Indicates if the given emoji shortcut is valid"""
    return len(shortcut) >= 2 and re.fullmatch(r"^[a-zA-Z0-9_]+$", shortcut)


def get_images_from_msg(msg: ipy.Message) -> list[ipy.Attachment | ipy.Embed]:
    images = [i for i in msg.attachments + msg.embeds if is_image(i)]
    if len(images) < 1 or len(images) > 5:
        raise BotUsageError("Message must contain between 1 to 5 attachments")
    return images
