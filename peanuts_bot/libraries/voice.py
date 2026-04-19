import io
import logging

from gtts import gTTS  # type: ignore[import-untyped]


logger = logging.getLogger(__name__)


def generate_tts_audio(text: str) -> io.BytesIO:
    """Generates TTS audio and returns it as an in-memory buffer"""

    if len(text) > 64:
        raise ValueError("only tts < 64 characters supported")

    buf = io.BytesIO()
    tts = gTTS(text, tld="co.uk")
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf
