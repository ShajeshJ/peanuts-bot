import asyncio
from dataclasses import dataclass
import io
import logging
import re
import traceback

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from peanuts_bot.config import CONFIG
from peanuts_bot.errors import BotUsageError, SOMETHING_WRONG, handle_interaction_error
from peanuts_bot.libraries.discord.messaging import (
    disable_message_components,
    is_messagable,
)
from peanuts_bot.libraries.image import (
    MAX_EMOJI_FILE_SIZE,
    ImageType,
    get_image_url,
    get_image_metadata,
    is_image,
)

__all__ = ["EmojiExtension"]

logger = logging.getLogger(__name__)

APPROVE_EMOJI_BTN = "approve_emoji_btn"
REJECT_EMOJI_BTN = "deny_emoji_btn"
SHORTCUT_TEXT_PREFIX = "shortcut_value_"

_LABEL_PREFIX = "shortcut for "


@dataclass
class EmojiRequest:
    """Holds the contextual information for a given Emoji Request"""

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
        """Creates an EmojiRequest from a message created by `EmojiRequest.to_approval_msg()`"""

        def _re_search(
            pattern: str | re.Pattern[str], string: str, flags: int | re.RegexFlag = 0
        ) -> re.Match[str]:
            match = re.search(pattern, string, flags)
            if not match:
                raise ValueError("unable to parse message as an emoji request")
            return match

        try:
            shortcut = _re_search(r"> shortcut: (.*)", msg).group(1)
            url = _re_search(r"> url: (.*)", msg).group(1)
            requester_id = int(_re_search(r"> requester_id: (.*)", msg).group(1))
            channel_id = int(_re_search(r"> channel_id: (.*)", msg).group(1))
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


def _get_file_name(img: discord.Attachment | discord.Embed) -> str:
    if isinstance(img, discord.Attachment):
        filename = img.filename
    elif img.url:
        filename = img.url.split("/")[-1]
    else:
        filename = "untitled"
    max_len = 45 - len(_LABEL_PREFIX)
    return filename if len(filename) <= max_len else f"...{filename[3 - max_len :]}"


class _EmojiNamesModal(discord.ui.Modal, title="Emoji Names"):
    def __init__(
        self, images: list[discord.Attachment | discord.Embed], channel_id: int
    ) -> None:
        super().__init__()
        self._images = images
        self._channel_id = channel_id
        for i, img in enumerate(images):
            self.add_item(
                discord.ui.TextInput(
                    label=f"{_LABEL_PREFIX}{_get_file_name(img)}",
                    custom_id=f"{SHORTCUT_TEXT_PREFIX}{i}",
                    style=discord.TextStyle.short,
                    placeholder="Leave blank to skip this image",
                    required=False,
                )
            )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer(ephemeral=True)

            values = {
                item.custom_id: item.value
                for item in self.children
                if isinstance(item, discord.ui.TextInput)
            }

            emoji_requests = []
            for field_id, shortcut in values.items():
                if not shortcut:
                    continue
                index = int(field_id.replace(SHORTCUT_TEXT_PREFIX, ""))
                url = get_image_url(self._images[index])
                if not url:
                    continue
                content_type, content_length = await get_image_metadata(url)
                req = EmojiRequest(
                    shortcut=shortcut,
                    url=url,
                    file_type=content_type,
                    file_len=content_length,
                    requester_id=interaction.user.id,
                    channel_id=self._channel_id,
                )
                emoji_requests.append(_request_emoji(req, interaction))

            if not emoji_requests:
                await interaction.followup.send(
                    "No emoji requests sent", ephemeral=True
                )
                return

            errors = [
                e
                for e in await asyncio.gather(*emoji_requests, return_exceptions=True)
                if isinstance(e, Exception)
            ]

            if not errors:
                await interaction.followup.send("Emoji requests sent", ephemeral=True)
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
            await interaction.followup.send(
                f"The following errors occurred: {''.join(error_strs)}", ephemeral=True
            )
        except Exception as e:
            await handle_interaction_error(interaction, e)


class _EmojiRejectModal(discord.ui.Modal, title="Reject Emoji"):
    reason: discord.ui.TextInput = discord.ui.TextInput(
        label="Rejection Reason",
        style=discord.TextStyle.paragraph,
        required=True,
        placeholder="Emoji is weirdly sized.",
        min_length=1,
    )

    def __init__(self, approval_message: discord.Message) -> None:
        super().__init__()
        self._approval_message = approval_message

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            try:
                emoji_request = EmojiRequest.from_approval_msg(
                    self._approval_message.content
                )
            except ValueError as e:
                raise BotUsageError("invalid emoji request message") from e

            channel = await interaction.client.fetch_channel(emoji_request.channel_id)
            guild = interaction.client.get_guild(CONFIG.GUILD_ID)
            if not guild or not is_messagable(channel):
                raise BotUsageError("unable to reject emoji request")

            requester = await guild.fetch_member(emoji_request.requester_id)
            if not requester:
                raise BotUsageError("unable to reject emoji request")

            await channel.send(
                f'{requester.mention} your emoji "{emoji_request.shortcut}" was rejected with reason:\n> {self.reason.value}'
            )
            await interaction.response.send_message(
                f"rejected emoji {emoji_request.shortcut}", ephemeral=True
            )
            await disable_message_components(self._approval_message)
        except Exception as e:
            await handle_interaction_error(interaction, e)


class _EmojiApprovalView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Approve", style=discord.ButtonStyle.success, custom_id=APPROVE_EMOJI_BTN
    )
    async def approve_emoji(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not interaction.message:
            raise BotUsageError("unable to fetch message")

        try:
            emoji_request = EmojiRequest.from_approval_msg(interaction.message.content)
        except ValueError as e:
            raise BotUsageError("invalid emoji request message") from e

        channel = await interaction.client.fetch_channel(emoji_request.channel_id)
        guild = interaction.client.get_guild(CONFIG.GUILD_ID)
        if not guild or not is_messagable(channel):
            raise BotUsageError("unable to fulfill emoji request")

        requester = await guild.fetch_member(emoji_request.requester_id)
        if not requester:
            raise BotUsageError("unable to fulfill emoji request")

        async with aiohttp.request("GET", emoji_request.url) as res:
            image_data = await res.read()

        emoji = await guild.create_custom_emoji(
            name=emoji_request.shortcut or "BADNAME",
            image=image_data,
            reason=f"Created by {requester.display_name} via bot commands",
        )
        await channel.send(f"{requester.mention} emoji {emoji} was created")
        await interaction.response.send_message(
            f"approved emoji {emoji_request.shortcut}", ephemeral=True
        )
        await disable_message_components(interaction.message)

    @discord.ui.button(
        label="Deny", style=discord.ButtonStyle.danger, custom_id=REJECT_EMOJI_BTN
    )
    async def reject_emoji(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not interaction.message:
            raise BotUsageError("unable to fetch message")
        await interaction.response.send_modal(_EmojiRejectModal(interaction.message))

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        await handle_interaction_error(interaction, error)


class EmojiExtension(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._ctx_menu = app_commands.ContextMenu(
            name="Convert to Emoji",
            callback=self._emoji_from_attachment,
        )

    async def cog_load(self) -> None:
        self.bot.tree.add_command(self._ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(
            "Convert to Emoji", type=discord.AppCommandType.message
        )

    @staticmethod
    def get_help_color() -> discord.Color:
        return discord.Color.from_str("#F1C40F")

    @app_commands.command(name="emoji")
    @app_commands.describe(
        shortcut="Shortcut for the emoji", image="Image of the emoji"
    )
    async def emoji_cmd(
        self, interaction: discord.Interaction, shortcut: str, image: discord.Attachment
    ) -> None:
        """Request a new Emoji to be added"""
        url = get_image_url(image)
        if not url:
            raise BotUsageError(
                "Not a valid file. Emoji images must be png, jpeg, or gif files."
            )

        content_type, content_length = await get_image_metadata(url)
        req = EmojiRequest(
            shortcut=shortcut,
            url=url,
            file_type=content_type,
            file_len=content_length,
            requester_id=interaction.user.id,
            channel_id=interaction.channel_id or 0,
        )
        await _request_emoji(req, interaction)
        await interaction.response.send_message("Emoji request sent", ephemeral=True)

    async def _emoji_from_attachment(
        self, interaction: discord.Interaction, message: discord.Message
    ) -> None:
        images = get_images_from_msg(message)
        await interaction.response.send_modal(
            _EmojiNamesModal(images, interaction.channel_id or 0)
        )


async def _request_emoji(req: EmojiRequest, interaction: discord.Interaction) -> None:
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

    admin_user = await interaction.client.fetch_user(CONFIG.ADMIN_USER_ID)
    if not admin_user:
        raise BotUsageError("unable to find bot admin user")
    await admin_user.send(req.to_approval_msg(), view=_EmojiApprovalView())


def is_valid_emoji_type(_type: ImageType) -> bool:
    return _type in [ImageType.JPEG, ImageType.PNG, ImageType.GIF]


def is_valid_shortcut(shortcut: str) -> bool:
    """Indicates if the given emoji shortcut is valid"""
    return bool(len(shortcut) >= 2 and re.fullmatch(r"^[a-zA-Z0-9_]+$", shortcut))


def get_images_from_msg(
    msg: discord.Message,
) -> list[discord.Attachment | discord.Embed]:
    media: list[discord.Attachment | discord.Embed] = [*msg.attachments, *msg.embeds]
    images = [i for i in media if is_image(i)]
    if len(images) < 1 or len(images) > 5:
        raise BotUsageError("Message must contain between 1 to 5 attachments")
    return images


async def setup(bot: commands.Bot) -> None:
    bot.add_view(_EmojiApprovalView())
    await bot.add_cog(EmojiExtension(bot))
