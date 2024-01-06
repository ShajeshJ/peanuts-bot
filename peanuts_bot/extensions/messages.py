from enum import Enum, auto
from functools import partial
import logging
import re
from typing import Annotated
import interactions as ipy

from peanuts_bot.config import CONFIG
from peanuts_bot.errors import BotUsageError
from peanuts_bot.libraries.discord_bot import (
    BAD_TWITTER_LINKS,
    DiscordMesageLink,
    get_discord_msg_links,
    parse_discord_msg_link,
)
from peanuts_bot.libraries.image import get_image_url

__all__ = ["MessageExtension"]

logger = logging.getLogger(__name__)


_LEAGUE_DROPDOWN = "league_ping_check"


class _LeagueOptions(Enum):
    YES = 0
    ARAM = auto()
    RANKED = auto()
    PENTA = auto()
    LATER = auto()
    NO = auto()

    @classmethod
    def get_dropdown_options(cls):
        return [
            ipy.StringSelectOption(label="I'm down", value=cls.YES.value, emoji=":white_check_mark:"),
            ipy.StringSelectOption(label="Aram only", value=cls.ARAM.value, emoji=":arrow_upper_right:"),
            ipy.StringSelectOption(label="Ranked only", value=cls.RANKED.value, emoji=":ladder:"),
            ipy.StringSelectOption(label="If penta", value=cls.PENTA.value, emoji=":five:"),
            ipy.StringSelectOption(label="Later", value=cls.LATER.value, emoji=":clock830:"),
            ipy.StringSelectOption(label="Nah", value=cls.NO.value, emoji=":x:"),
        ]


class MessageExtension(ipy.Extension):
    @staticmethod
    def get_help_color() -> ipy.Color:
        return ipy.FlatUIColors.CLOUDS

    @ipy.slash_command(
        scopes=[CONFIG.GUILD_ID],
        default_member_permissions=ipy.Permissions.ADMINISTRATOR,
    )
    async def speak(
        self,
        ctx: ipy.SlashContext,
        message: Annotated[
            str,
            ipy.slash_str_option(
                description="The message for the bot to repeat", required=True
            ),
        ],
    ):
        """[ADMIN-ONLY] Make the bot say something"""
        await ctx.send(message)

    @ipy.slash_command(
        scopes=[CONFIG.GUILD_ID],
        default_member_permissions=ipy.Permissions.ADMINISTRATOR,
    )
    async def messages(self, _: ipy.SlashContext):
        pass

    @messages.subcommand()
    async def delete(
        self,
        ctx: ipy.SlashContext,
        amount: Annotated[
            int,
            ipy.slash_int_option(
                description="**Caution against > 100**. The number of messages to delete.",
                min_value=1,
            ),
        ] = 1,
    ):
        """[ADMIN-ONLY] Deletes the last X messages in the channel"""

        await ctx.defer(ephemeral=True)
        num_deleted = await ctx.channel.purge(deletion_limit=amount)
        await ctx.send(f"Deleted {num_deleted} message(s)", ephemeral=True)

    @ipy.slash_command(scopes=[CONFIG.GUILD_ID])
    async def quote(
        self,
        ctx: ipy.SlashContext,
        link: Annotated[
            str,
            ipy.slash_str_option(
                description="The link to the message to quote", required=True
            ),
        ],
    ):
        """Quote a message"""

        parsed_link = parse_discord_msg_link(link)
        if not parsed_link:
            raise BotUsageError("Must provide a discord message link")

        message = await self._get_discord_msg(parsed_link)
        quote_as_embed = await _create_quote_embed(message)
        await ctx.send(embeds=quote_as_embed)

    @ipy.listen("on_message_create", delay_until_ready=True)
    async def auto_quote(self, event: ipy.events.MessageCreate):
        """Automatically quote any messages that contain a discord message link"""

        msg = event.message

        if msg.guild and msg.guild.id != CONFIG.GUILD_ID:
            return

        quote_as_embed = None

        for url in get_discord_msg_links(msg.content):
            try:
                quoted_msg = await self._get_discord_msg(url)
            except BotUsageError:
                logger.debug(
                    "url regex found match but could not fetch message from the url",
                    exc_info=True,
                )
                continue
            except ipy.errors.HTTPException:
                logger.warning(
                    "an api error occurred while trying to retrieve a message from a url",
                    exc_info=True,
                )
                continue

            quote_as_embed = await _create_quote_embed(quoted_msg)
            break

        if not quote_as_embed:
            return

        await msg.reply(embeds=quote_as_embed)

    @ipy.listen("on_message_create", delay_until_ready=True)
    async def auto_fix_twitter_links(self, event: ipy.events.MessageCreate):
        """Echo a message with fixed twitter links if needed"""

        msg = event.message

        if msg.guild and msg.guild.id != CONFIG.GUILD_ID:
            return

        if not any(bad_link in msg.content for bad_link in BAD_TWITTER_LINKS):
            return

        new_content = f"Message with fixed Twitter links:\n{msg.content}".replace("\n", "\n> ")
        for l in BAD_TWITTER_LINKS:
            new_content = new_content.replace(l, "https://fxtwitter.com")

        await msg.reply(content=new_content)


    @ipy.listen("on_message_create", delay_until_ready=True)
    async def send_league_ping_check(self, event: ipy.events.MessageCreate):
        """Send a ping check message if a message contains the word league"""

        if not CONFIG.LEAGUE_ROLE_ID:
            return

        msg = event.message

        if msg.guild and msg.guild.id != CONFIG.GUILD_ID:
            return

        async for r in msg.mention_roles:
            if r.id == CONFIG.LEAGUE_ROLE_ID:
                break
        else:
            return

        dropdown = ipy.StringSelectMenu(
            *_LeagueOptions.get_dropdown_options(),
            custom_id=_LEAGUE_DROPDOWN,
        )

        content = "\n".join(f"{o.emoji} {o.label}:" for o in dropdown.options)

        await msg.reply(content=content, components=[dropdown])


    @ipy.component_callback(_LEAGUE_DROPDOWN)
    async def league_ping_response(self, ctx: ipy.ComponentContext):
        """Callback of the response status after pinging for league"""
        selected = int(ctx.values[0])
        entry = f" {ctx.author.mention}"
        edit_message = ctx.edit_origin

        if selected == _LeagueOptions.LATER.value:
            modal = ipy.Modal(
                ipy.InputText(
                    custom_id="time",
                    label="When?",
                    style=ipy.TextStyles.SHORT,
                    placeholder="Leave blank to not specify",
                    required=False,
                ),
                custom_id=f"{_LEAGUE_DROPDOWN}_later",
                title="Confirm Time",
            )
            await ctx.send_modal(modal)
            modal_ctx = await ctx.bot.wait_for_modal(modal, ctx.author.id)
            edit_message = partial(modal_ctx.edit, ctx.message_id)

            if time := modal_ctx.responses.get("time"):
                entry += f" ({time})"

        # removes either " @user" or " @user (time)" from the message
        new_content = re.sub(rf" {ctx.author.mention}( \(.*?\))?", "", ctx.message.content)
        rows = new_content.split("\n")
        rows[selected] += entry
        await edit_message(content="\n".join(rows))


    async def _get_discord_msg(self, link: DiscordMesageLink) -> ipy.Message:
        """
        Gets the message object from the given link

        :param link: The link to get the message object from
        :param bot: The bot to use to fetch the message

        :raises BotUsageError: If the message cannot be found
        :return: The message object
        """
        if link.guild_id != CONFIG.GUILD_ID:
            raise BotUsageError("Cannot quote messages from other servers")

        ch = await self.bot.fetch_channel(link.channel_id)
        if not ch:
            raise BotUsageError("Message could not be found")

        message = await ch.fetch_message(link.message_id)
        if not message:
            raise BotUsageError("Message could not be found")

        return message


async def _create_quote_embed(msg: ipy.Message) -> ipy.Embed:
    """Construct an embed quote from a message object"""

    embed = ipy.Embed()

    # Set author
    embed.set_author(name=msg.author.display_name, icon_url=msg.author.avatar.url)

    try:
        image_url = next(
            url for i in msg.attachments + msg.embeds if (url := get_image_url(i))
        )
        embed.set_image(url=image_url)
    except StopIteration:
        pass

    # Set quoted message content with a link to the original
    embed.description = msg.content
    embed.description += "\n\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\n"
    embed.description += f"[**View Original**]({str(msg.jump_url)})"

    # Set footer with origin channel and message timestamp
    embed.set_footer(text=f"in #{msg.channel.name}")
    embed.timestamp = msg.edited_timestamp or msg.timestamp

    return embed
