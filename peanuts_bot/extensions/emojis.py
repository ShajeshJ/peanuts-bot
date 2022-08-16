import asyncio
from dataclasses import dataclass, field
import logging
import traceback
import aiohttp
import re
from typing import Annotated
from uuid import uuid4
import interactions as ipy
import interactions.ext.enhanced as ipye

from config import CONFIG
from peanuts_bot.constants.bot import MAX_EMOJI_FILE_SIZE_IN_BYTES, SOMETHING_WRONG
from peanuts_bot.errors import BotUsageError
from peanuts_bot.libraries.bot_messaging import (
    disable_all_components,
    get_emoji_mention,
)
from peanuts_bot.libraries import storage
from peanuts_bot.libraries.image import (
    ImageType,
    is_image,
    get_image_url,
    get_image_metadata,
)


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

    @ipy.extension_message_command(name="Convert to Emoji", scope=CONFIG.GUILD_ID)
    async def emoji_from_attachment(self, ctx: ipy.CommandContext):
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
                channel_id=ctx.channel.id,
            )
            storage.put(req._id, req)
            tracking_id = req._id

            label = f"Emoji name to give to image {i+1}"

            text_fields.append(
                ipy.TextInput(
                    custom_id=f"{SHORTCUT_TEXT_PREFIX}{tracking_id}",
                    label=label,
                    style=ipy.TextStyleType.SHORT,
                    placeholder="Leave blank to skip this image",
                    required=False,
                )
            )

        await ctx.popup(
            ipy.Modal(
                custom_id=SHORTCUT_MODAL,
                title="Emoji Names",
                components=text_fields,
            )
        )

    @ipy.extension_modal(SHORTCUT_MODAL)
    async def emoji_from_attachment_modal(self, ctx: ipy.CommandContext, *_):
        """Use the shortcut names to complete the emoji request submissions"""

        outcomes = []

        for row in ctx.data.components:
            # each row in a modal has just the single text field
            field: ipy.Component = row.components[0]
            tracking_id = field.custom_id.replace(SHORTCUT_TEXT_PREFIX, "")
            shortcut = field.value

            if not shortcut:
                storage.pop(tracking_id)
                continue

            req: EmojiRequest = storage.get(tracking_id)
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

    @ipy.extension_component(APPROVE_EMOJI_PREFIX, startswith=True)
    async def approve_emoji(self, ctx: ipy.ComponentContext):
        """Callback of an admin approving an emoji"""

        tracking_id = ctx.custom_id.replace(APPROVE_EMOJI_PREFIX, "")
        emoji_request: EmojiRequest = storage.pop(tracking_id)

        # Refresh potentially stale objects using id
        channel = await ipy.get(
            self.client, ipy.Channel, object_id=emoji_request.channel_id
        )
        requester = await ipy.get(
            self.client, ipy.User, object_id=emoji_request.requester_id
        )
        guild = next(g for g in self.client.guilds if g.id == CONFIG.GUILD_ID)

        async with aiohttp.request("GET", emoji_request.url) as res:
            filename = f"{emoji_request.shortcut}{emoji_request.file_type.extension}"

            emoji = await guild.create_emoji(
                ipy.Image(filename, await res.content.read()),
                emoji_request.shortcut,
                reason=f"Created by {requester.username} via bot comands",
            )
            await channel.send(
                f"{requester.mention} emoji {get_emoji_mention(emoji)} was created"
            )

        components = disable_all_components(ctx.message.components)

        await ctx.edit(components=components)

    @ipy.extension_component(REJECT_EMOJI_PREFIX, startswith=True)
    async def reject_emoji(self, ctx: ipy.ComponentContext):
        """Callback of an admin rejecting an emoji"""

        tracking_id = ctx.custom_id.replace(REJECT_EMOJI_PREFIX, "")
        await ctx.popup(
            ipy.Modal(
                custom_id=f"{MODAL_REJECT_EMOJI_PREFIX}{tracking_id}",
                title="Reject Emoji",
                components=[
                    ipy.TextInput(
                        custom_id="emoji_reject_reason",
                        label="Rejection Reason",
                        style=ipy.TextStyleType.PARAGRAPH,
                        required=True,
                        placeholder="Emoji is weirdly sized.",
                        min_length=1,
                    )
                ],
            )
        )

    @ipy.extension_modal(MODAL_REJECT_EMOJI_PREFIX, startswith=True)
    async def reject_emoji_modal(self, ctx: ipy.CommandContext):
        """Callback after admin filled out error reason for an emoji rejection"""

        reason = ctx.data.components[0].components[0].value

        tracking_id = ctx.data.custom_id.replace(MODAL_REJECT_EMOJI_PREFIX, "")
        emoji_request: EmojiRequest = storage.pop(tracking_id)

        # Refresh potentially stale objects using id
        channel = await ipy.get(
            self.client, ipy.Channel, object_id=emoji_request.channel_id
        )
        requester = await ipy.get(
            self.client, ipy.User, object_id=emoji_request.requester_id
        )

        # Original message with Approve/Deny buttons
        request_msg = ctx.message

        await channel.send(
            f'{requester.mention} your emoji "{emoji_request.shortcut}" was rejected with reason:\n> {reason}'
        )
        await ctx.send("Rejection response sent", ephemeral=True)

        components = disable_all_components(request_msg.components)
        await request_msg.edit(components=components)


async def _request_emoji(
    req: EmojiRequest, ctx: ipy.CommandContext | ipy.ComponentContext
):
    """
    Sends a emoji creation request to the guild's Admin User

    :param req: The emoji request to be made
    :param ctx: The current command context

    :return: If the emoji could not be added, the string returned is the rejection reason.
    """
    logger.debug(f"File type: {req.file_type}")
    if not is_valid_emoji_type(req.file_type):
        raise BotUsageError(
            "Not a valid file. Emoji images must be png, jpeg, or gif files."
        )

    logger.debug(f"File size: {req.file_len}")
    if req.file_len > MAX_EMOJI_FILE_SIZE_IN_BYTES:
        raise BotUsageError(f"File is too large. Emoji images must be < 2MB")

    if not req.shortcut or not is_valid_shortcut(req.shortcut):
        raise BotUsageError(
            f"{req.shortcut} is not a valid shortcut. Emoji Shortcuts must be alphanumeric or underscore characters only."
        )

    storage.put(req._id, req)
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

    admin_user = await ctx.guild.get_member(CONFIG.ADMIN_USER_ID)
    await admin_user.send(
        f"{ctx.author.name} requested to create the emoji {req.url} with the shortcut '{req.shortcut}'",
        components=[yes_btn, no_btn],
    )


def is_valid_emoji_type(_type: ImageType) -> bool:
    return _type in [ImageType.JPEG, ImageType.PNG, ImageType.GIF]


def is_valid_shortcut(shortcut: str) -> bool:
    """Indicates if the given emoji shortcut is valid"""
    return len(shortcut) >= 2 and re.fullmatch(r"^[a-zA-Z0-9_]+$", shortcut)


def setup(client: ipy.Client):
    EmojiExtensions(client)
