import asyncio
from dataclasses import dataclass, field
import logging
import traceback
import aiohttp
import re
from typing import Annotated
from uuid import uuid4
import interactions as ipy

from config import CONFIG
from peanuts_bot.errors import BotUsageError, SOMETHING_WRONG
from peanuts_bot.libraries.discord_bot import disable_all_components
from peanuts_bot.libraries.storage import Storage
from peanuts_bot.libraries.image import (
    MAX_EMOJI_FILE_SIZE,
    ImageType,
    is_image,
    get_image_url,
    get_image_metadata,
)

__all__ = ["setup", "EmojiExtensions"]

logger = logging.getLogger(__name__)

APPROVE_EMOJI_PREFIX = "approve_emoji_"
REJECT_EMOJI_PREFIX = "deny_emoji_"
SHORTCUT_MODAL = "shortcut_data_modal"
SHORTCUT_TEXT_PREFIX = "shortcut_value_"
MODAL_REJECT_EMOJI_PREFIX = "reject_emoji_modal_"


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
    _id: str = field(default_factory=lambda: uuid4().hex)


STORAGE = Storage[EmojiRequest]()


class EmojiExtensions(ipy.Extension):
    def __init__(self, client: ipy.Client) -> None:
        self.client: ipy.Client = client

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

        images = [i for i in ctx.target.attachments + ctx.target.embeds if is_image(i)]
        if len(images) < 1 or len(images) > 5:
            raise BotUsageError("Message must contain between 1 to 5 attachments")

        text_fields = []

        for i, img in enumerate(images):
            url = get_image_url(img)
            content_type, content_length = await get_image_metadata(url)

            req = EmojiRequest(
                shortcut=None,
                url=url,
                file_type=content_type,
                file_len=content_length,
                requester_id=ctx.author.id,
                channel_id=ctx.channel_id,
            )
            STORAGE.put(req._id, req)
            tracking_id = req._id

            label = f"Emoji name to give to image {i+1}"

            text_fields.append(
                ipy.InputText(
                    custom_id=f"{SHORTCUT_TEXT_PREFIX}{tracking_id}",
                    label=label,
                    style=ipy.TextStyles.SHORT,
                    placeholder="Leave blank to skip this image",
                    required=False,
                )
            )

        await ctx.send_modal(
            ipy.Modal(
                *text_fields,
                custom_id=SHORTCUT_MODAL,
                title="Emoji Names",
            )
        )

    @ipy.modal_callback(SHORTCUT_MODAL)
    async def emoji_from_attachment_modal(self, ctx: ipy.ModalContext, **_):
        """Use the shortcut names to complete the emoji request submissions"""

        outcomes = []

        for custom_id, shortcut in ctx.responses.items():
            tracking_id = custom_id.replace(SHORTCUT_TEXT_PREFIX, "")

            if not shortcut:
                STORAGE.pop(tracking_id)
                continue

            req = STORAGE.get(tracking_id)
            if not req:
                continue

            req.shortcut = shortcut
            outcomes.append(_request_emoji(req, ctx))

        if not outcomes:
            await ctx.send("No emoji requests sent", ephemeral=True)
            return

        errors = [
            e
            for e in await asyncio.gather(*outcomes, return_exceptions=True)
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
            f"The following errors occurred: {''.join(error_strs)}",
            ephemeral=True,
        )

    @ipy.component_callback(re.compile(f"{APPROVE_EMOJI_PREFIX}.*"))
    async def approve_emoji(self, ctx: ipy.ComponentContext):
        """Callback of an admin approving an emoji"""

        tracking_id = ctx.custom_id.replace(APPROVE_EMOJI_PREFIX, "")
        disabled_btns = disable_all_components(ctx.message.components)
        emoji_request = STORAGE.pop(tracking_id)

        if not emoji_request:
            await ctx.message.edit(components=disabled_btns)
            raise BotUsageError("Unable to find emoji request")

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

    @ipy.component_callback(re.compile(f"{REJECT_EMOJI_PREFIX}.*"))
    async def reject_emoji(self, ctx: ipy.ComponentContext):
        """Callback of an admin rejecting an emoji"""

        tracking_id = ctx.custom_id.replace(REJECT_EMOJI_PREFIX, "")
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
                custom_id=f"{MODAL_REJECT_EMOJI_PREFIX}{tracking_id}",
                title="Reject Emoji",
            )
        )

    @ipy.modal_callback(re.compile(f"{MODAL_REJECT_EMOJI_PREFIX}.*"))
    async def reject_emoji_modal(self, ctx: ipy.ModalContext, emoji_reject_reason: str):
        """Callback after admin filled out error reason for an emoji rejection"""

        tracking_id = ctx.custom_id.replace(MODAL_REJECT_EMOJI_PREFIX, "")
        disabled_btns = disable_all_components(ctx.message.components)
        emoji_request = STORAGE.pop(tracking_id)

        if not emoji_request:
            await ctx.message.edit(components=disabled_btns)
            raise BotUsageError("Unable to find emoji request")

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

    STORAGE.put(req._id, req)
    tracking_id = req._id

    yes_btn = ipy.Button(
        label="Approve",
        style=ipy.ButtonStyle.SUCCESS,
        custom_id=f"{APPROVE_EMOJI_PREFIX}{tracking_id}",
    )

    no_btn = ipy.Button(
        label="Deny",
        style=ipy.ButtonStyle.DANGER,
        custom_id=f"{REJECT_EMOJI_PREFIX}{tracking_id}",
    )

    admin_user = await ctx.bot.fetch_user(CONFIG.ADMIN_USER_ID)
    await admin_user.send(
        f"{ctx.author.display_name} requested to create the emoji {req.url} with the shortcut '{req.shortcut}'",
        components=[yes_btn, no_btn],
    )


def is_valid_emoji_type(_type: ImageType) -> bool:
    return _type in [ImageType.JPEG, ImageType.PNG, ImageType.GIF]


def is_valid_shortcut(shortcut: str) -> bool:
    """Indicates if the given emoji shortcut is valid"""
    return len(shortcut) >= 2 and re.fullmatch(r"^[a-zA-Z0-9_]+$", shortcut)


def setup(client: ipy.Client):
    EmojiExtensions(client)
