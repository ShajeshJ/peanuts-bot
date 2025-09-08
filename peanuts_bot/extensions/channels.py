import asyncio
from enum import Enum
import functools
import logging
import os
from typing import Annotated
import interactions as ipy

from peanuts_bot.config import CONFIG
from peanuts_bot.errors import BotUsageError
from peanuts_bot.libraries.discord.admin import Features, has_features
from peanuts_bot.libraries.discord.voice import BotVoice
from peanuts_bot.libraries.voice import generate_tts_audio

__all__ = ["ChannelExtension"]

logger = logging.getLogger(__name__)


class VoiceAction(str, Enum):
    JOIN = "joined"
    LEAVE = "left"


class ChannelExtension(ipy.Extension):
    @staticmethod
    def get_help_color() -> ipy.Color:
        return ipy.FlatUIColors.PETERRIVER

    @ipy.slash_command(scopes=[CONFIG.GUILD_ID])
    async def channel(self, _: ipy.SlashContext):
        pass

    @channel.subcommand()
    async def create(
        self,
        ctx: ipy.SlashContext,
        name: Annotated[
            str,
            ipy.slash_str_option(
                description="The name of the new channel", required=True
            ),
        ],
        category: Annotated[
            ipy.GuildCategory | None,
            ipy.slash_channel_option(
                description="Category to nest the channel under",
                channel_types=[ipy.ChannelType.GUILD_CATEGORY],
            ),
        ] = None,
    ):
        """Create a new text channel"""

        if not ctx.guild:
            raise BotUsageError("This command can only be used in a server")

        existing_channel = next(
            (
                c
                for c in await ctx.guild.fetch_channels()
                if c.type != ipy.ChannelType.GUILD_CATEGORY and c.name == name
            ),
            None,
        )
        if existing_channel:
            raise BotUsageError(f"{existing_channel.mention} already exists")

        create_channel = functools.partial(
            ctx.guild.create_channel,
            channel_type=ipy.ChannelType.GUILD_TEXT,
            name=name,
            reason=f"Created by {ctx.author.display_name} via bot commands",
        )

        if category:
            channel = await create_channel(category=category)
        else:
            channel = await create_channel()

        await ctx.send(f"Created new channel {channel.mention}")

    @ipy.listen(ipy.events.VoiceStateUpdate, delay_until_ready=True)
    async def announce_user_move(self, event: ipy.events.VoiceStateUpdate):
        """Announces when a user moves channels"""

        logger.debug("voice state update event")

        guild = event.bot.get_guild(CONFIG.GUILD_ID)
        if not await has_features(Features.VOICE_ANNOUNCER, guild=guild):
            logger.debug("voice_announcer feature is not enabled")
            return

        if not event.before or not event.after:
            logger.debug("ignoring voice state new/destroy event")
            return

        if event.before.channel.id == event.after.channel.id:
            logger.debug("not a channel update event. ignoring...")
            return

        if event.after.member.bot:
            logger.info("bot moved voice channels. ignoring...")
            return

        bot_vstate = event.bot.get_bot_voice_state(event.after.guild.id)
        if not bot_vstate or not bot_vstate.connected:
            logger.info("bot is not in a voice channel. joining...")
            bot_vstate = await event.bot.connect_to_vc(
                guild_id=event.after.guild.id,
                channel_id=event.after.channel.id,
                muted=False,
                deafened=True,
            )
            return

        if all(
            m.id == event.after.member.id or m.bot
            for m in bot_vstate.channel.voice_members
        ):
            logger.info("bot is in an empty voice channel. moving to this channel...")
            bot_vstate = await event.bot.connect_to_vc(
                guild_id=event.after.guild.id,
                channel_id=event.after.channel.id,
                muted=False,
                deafened=True,
            )
            return

        if bot_vstate.channel.id != event.after.channel.id:
            logger.info("user moved into another channel. ignoring...")
            return

        await self._play_announcer_audio(event.after.member, VoiceAction.JOIN)

    @ipy.listen(ipy.events.VoiceUserJoin, delay_until_ready=True)
    async def announce_user_join(self, event: ipy.events.VoiceUserJoin):
        """Announces when a user joins a voice channel"""

        logger.debug(
            f"voice connecting event {event.channel.name}, {event.author.username}"
        )

        guild = event.bot.get_guild(CONFIG.GUILD_ID)
        if not await has_features(Features.VOICE_ANNOUNCER, guild=guild):
            logger.debug("voice_announcer feature is not enabled")
            return

        if event.author.bot:
            logger.info("bot joined a voice channel. ignoring...")
            return

        bot_vstate = event.bot.get_bot_voice_state(event.channel.guild.id)
        if not bot_vstate or not bot_vstate.connected:
            logger.info("bot is joining the channel")
            await event.bot.connect_to_vc(
                guild_id=event.channel.guild.id,
                channel_id=event.channel.id,
                muted=False,
                deafened=True,
            )
            return

        if bot_vstate.channel.id != event.channel.id:
            logger.info("user joined another channel. ignoring...")
            return

        await self._play_announcer_audio(event.author, VoiceAction.JOIN)

    @ipy.listen(ipy.events.VoiceUserLeave, delay_until_ready=True)
    async def bot_leave(self, event: ipy.events.VoiceUserLeave):
        """Ensures the bot leaves a voice channel if there are no connected users"""

        logger.debug(
            f"voice disconnecting event {event.channel.name}, {event.author.username}"
        )

        guild = event.bot.get_guild(CONFIG.GUILD_ID)
        if not await has_features(Features.VOICE_ANNOUNCER, guild=guild):
            logger.debug("voice_announcer feature is not enabled")
            return

        if event.author.bot:
            logger.info("bot left a voice channel. ignoring...")
            return

        bot_vstate = event.bot.get_bot_voice_state(event.channel.guild.id)
        if not bot_vstate:
            logger.debug("bot is not in a voice channel. ignoring...")
            return

        if event.channel.id != bot_vstate.channel.id:
            logger.info("bot is in another channel. ignoring...")
            return

        if any(
            m
            for m in event.channel.voice_members
            if m.id != event.author.id and not m.bot
        ):
            logger.info(
                "active members are still in the voice channel. remaining in the channel..."
            )
            logger.debug(
                f"remaining voice members: {[m.username for m in event.channel.voice_members]}"
            )
            return

        logger.info("no users remaining. bot is disconnecting")
        await event.channel.disconnect()

    async def _play_announcer_audio(
        self, user: ipy.User | ipy.Member, action: VoiceAction
    ):
        await asyncio.sleep(1)
        logger.info("announcing user arrival")

        try:
            audio_file = generate_tts_audio(f"{user.username} has {action.value}")
        except ValueError:
            logger.warning("failed to play announcer audio", exc_info=True)
            return

        async def cleanup_file(_) -> None:
            try:
                os.remove(audio_file)
            except:
                logger.warning("failed to clean up audio file", exc_info=True)

        BotVoice().queue_audio(audio_file, cleanup_file)
