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
    # TODO: switch to BytesIO via tts.write_to_fp() + FFmpegPCMAudio(pipe=True) after migration is complete
    filename = f"{str(uuid.uuid4())}.mp3"
    tts.save(filename)

    return filename


def build_cleanup_callback(filename: str) -> Callable[[typing.Any], Awaitable[None]]:
    async def _cleanup_file(_) -> None:
        try:
            os.remove(filename)
        except:
            logger.warning("failed to clean up audio file", exc_info=True)

    return _cleanup_file
