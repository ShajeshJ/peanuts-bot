import asyncio
from collections.abc import Awaitable, Callable, Generator
from dataclasses import dataclass
import logging
import queue
import typing

import interactions as ipy
import interactions.api.voice.audio as ipyaudio

from peanuts_bot.config import CONFIG
from peanuts_bot.libraries.discord.admin import Features, has_features
from peanuts_bot.libraries.voice import build_cleanup_callback, generate_tts_audio


logger = logging.getLogger(__name__)


@dataclass
class _Work:
    filename: str
    callback: Callable[[ipy.Client], Awaitable[typing.Any]] | None = None


class BotVoice:
    """A global voice client that controls the bot's voice.
    The client ensures that audio tracks are queued such that the bot
    will complete each audio track before it attempts to play the next one.

    To use, the client must first be initialized during application bootup

    ```python
    bot = interactions.Client(...)
    BotVoice.init(bot)
    ```

    Then when you want to queue a new audio file, do the following:

    ```python
    voice = BotVoice()
    voice.queue_audio(filename)
    ```
    """

    _client: ipy.Client
    _audio_queue: queue.Queue[_Work]
    _queue_worker: asyncio.Task[None] | None = None

    _instance: typing.ClassVar["BotVoice | None"] = None
    __init_flag: typing.ClassVar[bool] = False

    def __new__(cls):
        if cls.__init_flag:
            cls._instance = super().__new__(cls)
            cls.__init_flag = False

        if not cls._instance:
            raise RuntimeError(f"BotVoice must first be initialized by calling `init`")

        return cls._instance

    @classmethod
    def init(cls, client: ipy.Client) -> None:
        """Initialize the BotVoice client"""
        cls.__init_flag = True
        voice_client = cls()
        voice_client._client = client
        voice_client._audio_queue = queue.Queue()

    def queue_audio(
        self,
        filename: str,
        callback: Callable[[ipy.Client], Awaitable[typing.Any]] | None = None,
    ) -> None:
        """Queues an audio file to be played by the Bot in
        whatever voice channel it's connected to.

        The bot will process each audio file in the queue in order
        and attempt to play it.

        Once the audio file plays entirely (or if it fails to play at all),
        the provided callback will be called.
        """
        self._audio_queue.put(_Work(filename, callback), block=False)
        logger.info(f"{filename} queued")

        if self._queue_worker:
            logger.debug("queue worker is already running... skipping...")
            return

        def clear_worker_ref(_):
            self._queue_worker = None

        self._queue_worker = asyncio.create_task(self.__process_queue())
        self._queue_worker.add_done_callback(clear_worker_ref)

    async def __process_queue(self):
        try:
            work: _Work | None = self._audio_queue.get(block=False)
        except:
            logger.warning("audio worker ran without any work queued")
            return

        async def _play_audio(_work: _Work):
            bot_vstate = self._client.get_bot_voice_state(CONFIG.GUILD_ID)
            if not bot_vstate:
                logger.warning(
                    "audio was not played because bot is not in a voice channel"
                )
                return

            arrival_audio = ipyaudio.AudioVolume(_work.filename)
            logger.info(f"playing {_work.filename}")
            await bot_vstate.play(arrival_audio)

        while work:
            try:
                await _play_audio(work)
            except:
                logger.warning(
                    "an error occurred while attempting to play the given audio",
                    exc_info=True,
                )
            finally:
                try:
                    if work.callback:
                        await work.callback(self._client)
                except:
                    logger.warning(
                        "an error occurred while running the callback", exc_info=True
                    )

            try:
                work = self._audio_queue.get(block=False)
            except:
                logger.info("no more audio work to process")
                work = None


def get_active_user_ids(
    bot_vstate: ipy.ActiveVoiceState,
) -> Generator[ipy.Snowflake, None, None]:
    """Returns a list of non-bot user ids in the given voice state"""
    return (m.id for m in bot_vstate.channel.voice_members if not m.bot)


def get_most_active_voice_channel(bot: ipy.Client) -> ipy.GuildVoice | None:
    """Will get the voice channel with greatest number of non-bot users connected.

    Returns None if there are no voice channels with users
    """

    guild = bot.get_guild(CONFIG.GUILD_ID)
    if not guild:
        return None

    vcs = [
        (ch, sum(1 for m in ch.voice_members if not m.bot))
        for ch in guild.channels
        if isinstance(ch, ipy.GuildVoice)
    ]

    if not vcs:
        return None

    most_active_vc, num_members = max(vcs, key=lambda vc_and_members: vc_and_members[1])

    return most_active_vc if num_members > 0 else None


@ipy.listen(ipy.events.Startup)
async def announcer_rejoin_on_startup(event: ipy.events.Startup):
    guild = event.bot.get_guild(CONFIG.GUILD_ID)
    if not guild or not await has_features(Features.VOICE_ANNOUNCER, guild=guild):
        return

    vc_to_join = get_most_active_voice_channel(event.bot)
    if not vc_to_join:
        return

    logger.info(f"Detected active voice channel on startup. Joining {vc_to_join.name}")
    await event.bot.connect_to_vc(guild.id, vc_to_join.id, muted=False, deafened=True)

    file = generate_tts_audio(f"{event.bot.user.username} restarted.")
    BotVoice().queue_audio(file, build_cleanup_callback(file))
