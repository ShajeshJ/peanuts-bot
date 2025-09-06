import uuid
import pyttsx3  # type: ignore[import-untyped]


def generate_tts_audio(text: str) -> str:
    """Generates a tts audio file on disk and returns the file path"""

    if len(text) > 64:
        raise ValueError("only tts < 64 characters supported")

    engine = pyttsx3.init(driverName="espeak")
    engine.setProperty("rate", 125)
    engine.setProperty("voice", "gmw/en-us")

    filename = f"{str(uuid.uuid4())}.wav"

    # Ideally, we can just save to a BytesIO
    # from testing, this is definitely by using
    # save_to_file, but passing `buffer = io.BytesIO()`
    # for the second argument.
    # However it looks like interaction-py isn't able to
    # play from an in-memory buffer.
    # TODO: see if we can figure out a way to pass a BytesIO
    # to interactions-py
    engine.save_to_file(text, filename)
    engine.runAndWait()

    return filename
