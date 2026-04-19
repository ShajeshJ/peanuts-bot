import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from peanuts_bot.errors import BotUsageError
from peanuts_bot.libraries.discord.admin import Features, has_features
from peanuts_bot.libraries.discord.voice import (
    BotVoice,
    get_active_user_ids,
    get_most_active_voice_channel,
)
from peanuts_bot.libraries.voice import generate_tts_audio

__all__ = ["ChannelExtension"]

logger = logging.getLogger(__name__)


def _get_bot_voice_channel(
    guild: discord.Guild,
) -> discord.VoiceChannel | discord.StageChannel | None:
    vc = guild.voice_client
    if isinstance(vc, discord.VoiceClient) and isinstance(
        vc.channel, (discord.VoiceChannel, discord.StageChannel)
    ):
        return vc.channel
    return None


class ChannelExtension(commands.Cog):
    _channel_group = app_commands.Group(
        name="channel", description="Channel management commands"
    )

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    def get_help_color() -> discord.Color:
        return discord.Color.from_str("#3498DB")

    @_channel_group.command(name="create")
    @app_commands.describe(
        name="The name of the new channel",
        category="Category to nest the channel under",
    )
    async def channel_create(
        self,
        interaction: discord.Interaction,
        name: str,
        category: Optional[discord.CategoryChannel] = None,
    ) -> None:
        """Create a new text channel"""
        if not interaction.guild:
            raise BotUsageError("This command can only be used in a server")

        existing_channel = next(
            (
                c
                for c in await interaction.guild.fetch_channels()
                if not isinstance(c, discord.CategoryChannel) and c.name == name
            ),
            None,
        )
        if existing_channel:
            raise BotUsageError(f"{existing_channel.mention} already exists")

        channel = await interaction.guild.create_text_channel(
            name=name,
            category=category,
            reason=f"Created by {interaction.user.display_name} via bot commands",
        )
        await interaction.response.send_message(
            f"Created new channel {channel.mention}"
        )

    @commands.Cog.listener("on_voice_state_update")
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.bot:
            return

        if not await has_features(Features.VOICE_ANNOUNCER, bot=self.bot):
            return

        guild = member.guild
        bot_channel = _get_bot_voice_channel(guild)

        joined = before.channel is None and after.channel is not None
        left = before.channel is not None and after.channel is None
        moved = (
            before.channel is not None
            and after.channel is not None
            and before.channel != after.channel
        )

        if joined and after.channel is not None:
            if bot_channel is None:
                await after.channel.connect(self_deaf=True)
            elif after.channel.id == bot_channel.id:
                BotVoice().queue_audio(
                    generate_tts_audio(f"{member.display_name} has joined.")
                )

        elif left and before.channel is not None:
            if bot_channel is None or before.channel.id != bot_channel.id:
                return
            vc = guild.voice_client
            if not isinstance(vc, discord.VoiceClient):
                return
            if get_active_user_ids(vc):
                return
            new_vc = get_most_active_voice_channel(self.bot)
            if new_vc is None:
                await vc.disconnect()
                return
            await vc.move_to(new_vc)
            bot_name = self.bot.user.name if self.bot.user else "Bot"
            BotVoice().queue_audio(generate_tts_audio(f"{bot_name} has joined."))

        elif moved and before.channel is not None and after.channel is not None:
            if bot_channel is None:
                return
            vc = guild.voice_client
            if not isinstance(vc, discord.VoiceClient):
                return
            if after.channel.id == bot_channel.id:
                BotVoice().queue_audio(
                    generate_tts_audio(f"{member.display_name} has joined.")
                )
            elif before.channel.id == bot_channel.id:
                if get_active_user_ids(vc):
                    return
                # follow user to their destination (not most-active search)
                await vc.move_to(after.channel)
                # announce the moving user only if others were already in destination
                other_users = [
                    uid for uid in get_active_user_ids(vc) if uid != member.id
                ]
                if other_users:
                    BotVoice().queue_audio(
                        generate_tts_audio(f"{member.display_name} has joined.")
                    )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChannelExtension(bot))
