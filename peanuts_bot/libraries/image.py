import base64
import io
import logging
from enum import Enum
import discord
import aiohttp


logger = logging.getLogger(__name__)


class ImageSize(int):
    @property
    def kb(self):
        return self / 1024

    @property
    def mb(self):
        return self / 1024**2

    @property
    def gb(self):
        return self / 1024**3

    def __str__(self) -> str:
        if self >= 1024**3:
            return f"{self.gb:.2f}".rstrip("0").rstrip(".") + " GB"
        elif self >= 1024**2:
            return f"{self.mb:.2f}".rstrip("0").rstrip(".") + " MB"
        elif self >= 1024:
            return f"{self.kb:.2f}".rstrip("0").rstrip(".") + " KB"
        else:
            return f"{self} B"


MAX_EMOJI_FILE_SIZE = ImageSize(256 * 1024)


class ImageType(str, Enum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    WEBP = "image/webp"
    OTHER = "image/..."

    @property
    def extension(self):
        return "." + self.replace("image/", "").split("+")[0]


def is_image(obj: discord.Attachment | discord.Embed) -> bool:
    """Indicates if a given attachment / embed object is an image"""

    if any(t.extension for t in ImageType if obj.url and obj.url.endswith(t.extension)):
        return True

    if isinstance(obj, discord.Attachment):
        return bool(obj.content_type and obj.content_type.startswith("image/"))

    return obj.type == "image"


def get_image_url(obj: discord.Attachment | discord.Embed) -> str | None:
    """Returns the URL of the image for an attachment / embed object, or None if no image is available"""

    if not is_image(obj):
        return None

    return obj.url


def decode_b64_image(image: str, *, filename: str | None = None) -> discord.File:
    """Converts a base64 string to a Discord file object

    Args:
        image: The base64 encoded image
        filename: The filename for the image. Defaults to None.

    Returns:
        A Discord file object containing the image as an io.BytesIO stream
    """
    if "data:image" in image:
        image = image.split(",")[1]

    return discord.File(io.BytesIO(base64.b64decode(image)), filename)


async def get_image_metadata(url: str) -> tuple[ImageType, int]:
    """Uses the headers of the given image url to get the content type and length of the image.

    Raises `ValueError` if the given URL does not have appropriate content headers for an image.
    """

    async with aiohttp.request("GET", url) as res:
        content_length = res.headers.get("Content-Length")
        mime = res.headers.get("Content-Type", "").split(";")[0].strip()

        logger.debug(f"Actual {mime=}, {content_length=}")

        if not content_length:
            raise ValueError("valid image metadata for the given URL")

        try:
            return ImageType(mime), int(content_length)
        except ValueError as e:
            if mime.startswith("image/"):
                return ImageType.OTHER, int(content_length)

            raise ValueError("Invalid image metadata for the given URL") from e
