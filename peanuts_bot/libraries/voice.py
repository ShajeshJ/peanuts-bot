from collections.abc import Awaitable, Callable
import logging
import os
import typing
import uuid
from gtts import gTTS  # type: ignore[import-untyped]


logger = logging.getLogger(__name__)


def generate_tts_audio(text: str) -> str:
    """Generates a tts audio file on disk and returns the file path"""

    if len(text) > 64:
        raise ValueError("only tts < 64 characters supported")

    tts = gTTS(text, tld="co.uk")
    filename = f"{str(uuid.uuid4())}.wav"

    # Ideally, we can just save to a BytesIO
    # from testing, which we can do by calling
    # tts.write_to_fp(...) instead.
    # However it looks like interaction-py isn't able to
    # play from an in-memory buffer.
    # TODO: see if we can figure out a way to pass a BytesIO
    # to interactions-py
    tts.save(filename)

    return filename


def build_cleanup_callback(filename: str) -> Callable[[typing.Any], Awaitable[None]]:
    async def _cleanup_file(_) -> None:
        try:
            os.remove(filename)
        except:
            logger.warning("failed to clean up audio file", exc_info=True)

    return _cleanup_file
