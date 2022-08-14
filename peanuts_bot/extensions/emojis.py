from dataclasses import dataclass, field
import logging
import aiohttp
import re
from typing import Annotated
from uuid import uuid4
import interactions as ipy
import interactions.ext.enhanced as ipye

from config import CONFIG
from peanuts_bot.constants.bot import MAX_EMOJI_FILE_SIZE_IN_BYTES
from peanuts_bot.libraries.bot_messaging import (
    disable_all_components,
    get_emoji_mention,
)
from peanuts_bot.libraries import storage


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
    emoji: ipy.Attachment
    requester: ipy.Member
    channel: ipy.Channel
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

        error = await self._request_emoji(shortcut, emoji, ctx)
        if error:
            await ctx.send(error, ephemeral=True)
            return

        await ctx.send("Emoji request sent", ephemeral=True)

    @ipy.extension_message_command(name="Convert to Emoji", scope=CONFIG.GUILD_ID)
    async def emoji_from_attachment(self, ctx: ipy.CommandContext):
        """Request to convert an attached image to an emoji"""

        if not isinstance(ctx.target, ipy.Message):
            raise TypeError("Message command's target must be a message")

        images = [a for a in ctx.target.attachments if is_image(a)]
        if len(images) < 1 or len(images) > 5:
            await ctx.send(
                "Message must contain between 1 to 5 attachments", ephemeral=True
            )
            return

        text_fields = []

        for i, img in enumerate(images):
            req = EmojiRequest(None, img, ctx.author, ctx.channel)
            storage.put(req._id, req)
            tracking_id = req._id

            label = f'Emoji name to give "{img.filename}"'
            if len(label) > 45:
                # Discord has label limit of 45
                label = f"Emoji name to give to image {i}"

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
            outcomes.append(await self._request_emoji(shortcut, req.emoji, ctx))

        errors = [f"\n- {e}" for e in outcomes if e is not None]

        if errors:
            await ctx.send(
                f"The following emojis could not be sent: {''.join(errors)}",
                ephemeral=True,
            )
        elif not outcomes:
            await ctx.send("No emoji requests sent", ephemeral=True)
        else:
            await ctx.send("Emoji requests sent", ephemeral=True)

    @ipy.extension_component(APPROVE_EMOJI_PREFIX, startswith=True)
    async def approve_emoji(self, ctx: ipy.ComponentContext):
        """Callback of an admin approving an emoji"""

        tracking_id = ctx.custom_id.replace(APPROVE_EMOJI_PREFIX, "")
        emoji_request: EmojiRequest = storage.pop(tracking_id)

        # Refresh potentially stale objects using id
        channel = await ipy.get(
            self.client, ipy.Channel, object_id=emoji_request.channel.id
        )
        requester = await ipy.get(
            self.client, ipy.User, object_id=emoji_request.requester.id
        )
        guild = next(g for g in self.client.guilds if g.id == CONFIG.GUILD_ID)

        async with aiohttp.request("GET", emoji_request.emoji.url) as res:
            filename = emoji_request.emoji.filename
            if filename.endswith(".jpg"):
                # Seems like `interactions-py` library has a bug where it doesn't support `.jpg` ending
                filename = filename[:-4] + ".jpeg"

            emoji = await guild.create_emoji(
                ipy.Image(filename, await res.content.read()),
                emoji_request.shortcut,
                reason=f"Created by {requester.username} via bot comands",
            )
            await channel.send(
                f"{requester.mention} emoji {get_emoji_mention(emoji)} was created"
            )

        components = disable_all_components(ctx.data.components)

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
            self.client, ipy.Channel, object_id=emoji_request.channel.id
        )
        requester = await ipy.get(
            self.client, ipy.User, object_id=emoji_request.requester.id
        )

        await channel.send(
            f'{requester.mention} your emoji "{emoji_request.shortcut}" was rejected with reason:\n> {reason}'
        )
        await ctx.send("Rejection response sent", ephemeral=True)

    async def _request_emoji(
        self,
        name: str,
        emoji: ipy.Attachment,
        ctx: ipy.CommandContext | ipy.ComponentContext,
    ) -> str | None:
        """
        Sends a emoji creation request to the guild's Admin User

        :param name: The name requested to give the emoji
        :param emoji: The image attachment of the emoji
        :param ctx: The current command context

        :return: If the emoji could not be added, the string returned is the rejection reason.
        """
        logger.debug(f"Emoji command file type {emoji.content_type}")

        if not is_image(emoji):
            return f"{emoji.filename} is not a valid file. Emoji images must be png, jpeg, or gif files."

        logger.debug(f"File size: {emoji.size}")
        if emoji.size > MAX_EMOJI_FILE_SIZE_IN_BYTES:
            return f"{emoji.filename} is too large to be an emoji. Emoji images must be < 2MB"

        if not is_valid_shortcut(name):
            return f"{name} is not a valid shortcut. Emoji Shortcuts must be alphanumeric or underscore characters only."

        req = EmojiRequest(name, emoji, ctx.author, ctx.channel)
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
            f"{ctx.author.name} requested to create the emoji {emoji.url} with the shortcut '{name}'",
            components=[yes_btn, no_btn],
        )


def is_image(attachment: ipy.Attachment) -> bool:
    """Indicates if a given attachment file is an image attachment"""
    return attachment.content_type in ["image/png", "image/jpeg", "image/gif"]


def is_valid_shortcut(shortcut: str) -> bool:
    """Indicates if the given emoji shortcut is valid"""
    return len(shortcut) >= 2 and re.fullmatch(r"^[a-zA-Z0-9_]+$", shortcut)


def setup(client: ipy.Client):
    EmojiExtensions(client)
