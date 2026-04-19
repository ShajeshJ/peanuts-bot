from enum import Enum, auto
import logging
import re
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from peanuts_bot.config import CONFIG
from peanuts_bot.errors import BotUsageError, handle_interaction_error
from peanuts_bot.libraries.discord.messaging import (
    BAD_TWITTER_LINKS,
    DiscordMesageLink,
    get_discord_msg_links,
    is_messagable,
    parse_discord_msg_link,
)

__all__ = ["MessageExtension"]

logger = logging.getLogger(__name__)

_LEAGUE_CHECK = "league_check"
_LEAGUE_DROPDOWN = f"{_LEAGUE_CHECK}_dropdown"
_LEAGUE_PING_BUTTON = f"{_LEAGUE_CHECK}_ping"

_MENTION_REGEX = re.compile(r"<@!?\d+>")


def _get_image_url(obj: discord.Attachment | discord.Embed) -> str | None:
    url = obj.url
    if not url:
        return None
    if any(
        url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp")
    ):
        return url
    if isinstance(obj, discord.Attachment):
        return (
            url if obj.content_type and obj.content_type.startswith("image/") else None
        )
    return url if obj.type == "image" else None


async def _create_quote_embed(msg: discord.Message) -> discord.Embed:
    embed = discord.Embed()

    avatar_url = (
        msg.author.avatar.url if msg.author.avatar else msg.author.default_avatar.url
    )
    embed.set_author(name=msg.author.display_name, icon_url=avatar_url)

    media: list[discord.Attachment | discord.Embed] = [*msg.attachments, *msg.embeds]
    image_url = next((url for obj in media if (url := _get_image_url(obj))), None)
    if image_url:
        embed.set_image(url=image_url)

    embed.description = msg.content
    embed.description += "\n\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\n"
    embed.description += f"[**View Original**]({msg.jump_url})"

    channel_name = getattr(msg.channel, "name", str(msg.channel.id))
    embed.set_footer(text=f"in #{channel_name}")
    embed.timestamp = msg.edited_at or msg.created_at

    return embed


async def _get_discord_msg(
    link: DiscordMesageLink, client: discord.Client
) -> discord.Message:
    if link.guild_id != CONFIG.GUILD_ID:
        raise BotUsageError("Cannot quote messages from other servers")

    ch = await client.fetch_channel(link.channel_id)
    if not is_messagable(ch):
        raise BotUsageError("Message could not be found")

    return await ch.fetch_message(link.message_id)


async def _league_ping_players(
    gamemode: Literal["Aram", "Ranked", "League"],
    bot_selection_msg: discord.Message,
    ignore: set[int],
) -> None:
    ignore.add(_LeagueOptions.NO.value)
    rows_to_notify = [
        r
        for i, r in enumerate(bot_selection_msg.content.split("\n"))
        if i not in ignore
    ]

    potential_mentions = " ".join(rows_to_notify).split(" ")
    mentions: set[str] = set()

    ref = bot_selection_msg.reference
    if ref and isinstance(ref.resolved, discord.Message):
        mentions.add(ref.resolved.author.mention)

    for m in potential_mentions:
        if _MENTION_REGEX.search(m):
            mentions.add(m)

    if not mentions:
        return

    await bot_selection_msg.reply(
        content=f"Gathering for {gamemode} {' '.join(mentions)}"
    )


class _LeagueOptions(int, Enum):
    YES = 0
    ARAM = auto()
    RANKED = auto()
    PENTA = auto()
    LATER = auto()
    NO = auto()

    @classmethod
    def get_dropdown_options(cls) -> list[discord.SelectOption]:
        return [
            discord.SelectOption(
                label="I'm down", value=str(cls.YES.value), emoji="✅"
            ),
            discord.SelectOption(
                label="Aram only", value=str(cls.ARAM.value), emoji="↗️"
            ),
            discord.SelectOption(
                label="Ranked only", value=str(cls.RANKED.value), emoji="🪜"
            ),
            discord.SelectOption(
                label="If penta", value=str(cls.PENTA.value), emoji="5️⃣"
            ),
            discord.SelectOption(label="Later", value=str(cls.LATER.value), emoji="🕣"),
            discord.SelectOption(label="Nah", value=str(cls.NO.value), emoji="❌"),
        ]


class _LeagueLaterModal(discord.ui.Modal, title="Confirm Time"):
    time_input: discord.ui.TextInput = discord.ui.TextInput(
        label="When?",
        style=discord.TextStyle.short,
        placeholder="Leave blank to not specify",
        required=False,
    )

    def __init__(
        self,
        selection_message: discord.Message,
        author: discord.Member | discord.User,
    ) -> None:
        super().__init__()
        self.selection_message = selection_message
        self.author = author

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            entry = f" {self.author.mention}"
            if self.time_input.value:
                entry += f" ({self.time_input.value})"

            new_content = re.sub(
                rf" {re.escape(self.author.mention)}( \(.*?\))?",
                "",
                self.selection_message.content,
            )
            rows = new_content.split("\n")
            rows[_LeagueOptions.LATER.value] += entry

            try:
                await self.selection_message.edit(content="\n".join(rows))
            except discord.HTTPException as e:
                if e.status not in (400, 404):
                    raise
                logger.info(f"Failed to edit league check message: {e}. Skipping...")

            await interaction.response.defer()
        except Exception as e:
            await handle_interaction_error(interaction, e)


class _LeaguePingView(discord.ui.View):
    def __init__(self, selection_message: discord.Message) -> None:
        super().__init__(timeout=300)
        self.selection_message = selection_message

    @discord.ui.button(label="Ranked", style=discord.ButtonStyle.success, emoji="🪜")
    async def ranked(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await _league_ping_players(
            "Ranked", self.selection_message, {_LeagueOptions.ARAM.value}
        )
        await interaction.response.edit_message(content="Ranked pinged!", view=None)

    @discord.ui.button(label="Aram", style=discord.ButtonStyle.primary, emoji="↗️")
    async def aram(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await _league_ping_players(
            "Aram", self.selection_message, {_LeagueOptions.RANKED.value}
        )
        await interaction.response.edit_message(content="Aram pinged!", view=None)

    @discord.ui.button(label="Either", style=discord.ButtonStyle.secondary, emoji="🤷")
    async def either(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await _league_ping_players("League", self.selection_message, set())
        await interaction.response.edit_message(content="League pinged!", view=None)

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        await handle_interaction_error(interaction, error)


class _LeagueDropdownView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.select(
        custom_id=_LEAGUE_DROPDOWN,
        placeholder="Are you down to play?",
        min_values=1,
        max_values=1,
        options=_LeagueOptions.get_dropdown_options(),
    )
    async def league_check_dropdown(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        selected = int(select.values[0])

        if not interaction.message:
            raise BotUsageError("Could not find original message")

        if selected == _LeagueOptions.LATER.value:
            await interaction.response.send_modal(
                _LeagueLaterModal(interaction.message, interaction.user)
            )
            return

        entry = f" {interaction.user.mention}"
        new_content = re.sub(
            rf" {re.escape(interaction.user.mention)}( \(.*?\))?",
            "",
            interaction.message.content,
        )
        rows = new_content.split("\n")
        rows[selected] += entry

        try:
            await interaction.response.edit_message(content="\n".join(rows))
        except discord.HTTPException as e:
            if e.status not in (400, 404):
                raise
            logger.info(f"Failed to edit league check message: {e}. Skipping...")

    @discord.ui.button(
        style=discord.ButtonStyle.primary,
        label="Ping to gather",
        emoji="📢",
        custom_id=_LEAGUE_PING_BUTTON,
    )
    async def league_check_ping(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not interaction.message:
            raise BotUsageError("Could not find original message")

        view = _LeaguePingView(interaction.message)
        await interaction.response.send_message(
            content="What game mode do you want to gather for?",
            view=view,
            ephemeral=True,
        )

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        await handle_interaction_error(interaction, error)


class MessageExtension(commands.Cog):
    _messages_group = app_commands.Group(
        name="messages",
        description="Message management commands",
        default_permissions=discord.Permissions(administrator=True),
    )

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    def get_help_color() -> discord.Color:
        return discord.Color.from_str("#ECF0F1")

    @commands.Cog.listener("on_message")
    async def auto_quote(self, msg: discord.Message) -> None:
        if msg.guild and msg.guild.id != CONFIG.GUILD_ID:
            return

        for url in get_discord_msg_links(msg.content):
            try:
                quoted_msg = await _get_discord_msg(url, self.bot)
            except BotUsageError:
                logger.debug(
                    "url regex found match but could not fetch message from the url",
                    exc_info=True,
                )
                continue
            except discord.HTTPException:
                logger.warning(
                    "an api error occurred while trying to retrieve a message from a url",
                    exc_info=True,
                )
                continue

            await msg.reply(embed=await _create_quote_embed(quoted_msg))
            return

    @commands.Cog.listener("on_message")
    async def auto_fix_twitter_links(self, msg: discord.Message) -> None:
        if msg.guild and msg.guild.id != CONFIG.GUILD_ID:
            return

        if not any(bad_link in msg.content for bad_link in BAD_TWITTER_LINKS):
            return

        new_content = f"Message with fixed Twitter links:\n{msg.content}".replace(
            "\n", "\n> "
        )
        for link in BAD_TWITTER_LINKS:
            new_content = new_content.replace(link, "https://fxtwitter.com")

        await msg.reply(content=new_content)
        await msg.edit(suppress=True)

    @commands.Cog.listener("on_message")
    async def send_league_ping_check(self, msg: discord.Message) -> None:
        if not CONFIG.LEAGUE_ROLE_ID:
            return

        if msg.guild and msg.guild.id != CONFIG.GUILD_ID:
            return

        if not any(r.id == CONFIG.LEAGUE_ROLE_ID for r in msg.role_mentions):
            return

        options = _LeagueOptions.get_dropdown_options()
        content = "\n".join(f"{o.emoji} {o.label}:" for o in options)

        await msg.reply(content=content, view=_LeagueDropdownView())

    @app_commands.command(name="speak")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(message="The message for the bot to repeat")
    async def speak(self, interaction: discord.Interaction, message: str) -> None:
        """[ADMIN-ONLY] Make the bot say something"""
        await interaction.response.send_message(message)

    @_messages_group.command(name="delete")
    @app_commands.describe(
        amount="**Caution against > 100**. The number of messages to delete."
    )
    async def messages_delete(
        self, interaction: discord.Interaction, amount: int = 1
    ) -> None:
        """[ADMIN-ONLY] Deletes the last X messages in the channel"""
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel | discord.Thread):
            raise BotUsageError("This command can only be used in a text channel")

        await interaction.response.defer(ephemeral=True)
        deleted = await channel.purge(limit=amount)
        await interaction.followup.send(
            f"Deleted {len(deleted)} message(s)", ephemeral=True
        )

    @app_commands.command(name="quote")
    @app_commands.describe(link="The link to the message to quote")
    async def quote(self, interaction: discord.Interaction, link: str) -> None:
        """Quote a message"""
        parsed_link = parse_discord_msg_link(link)
        if not parsed_link:
            raise BotUsageError("Must provide a discord message link")

        message = await _get_discord_msg(parsed_link, interaction.client)
        await interaction.response.send_message(
            embed=await _create_quote_embed(message)
        )


async def setup(bot: commands.Bot) -> None:
    bot.add_view(_LeagueDropdownView())
    await bot.add_cog(MessageExtension(bot))
