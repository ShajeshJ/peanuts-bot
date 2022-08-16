import logging
from enum import Enum
import interactions as ipy
import aiohttp


logger = logging.getLogger(__name__)


class ImageType(str, Enum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    SVG = "image/svg+xml"
    WEBP = "image/webp"

    @property
    def extension(self):
        return "." + self.replace("image/", "").split("+")[0]


def is_image(obj: ipy.Attachment | ipy.Embed) -> bool:
    """Indicates if a given attachment / embed object is an image"""

    if isinstance(obj, ipy.Attachment):
        return obj.content_type and obj.content_type.startswith("image/")

    return obj.type == "image"


def get_image_url(obj: ipy.Attachment | ipy.Embed):
    """Tries to return the URL of the image for an attachment / embed object, if available"""

    if not is_image(obj):
        raise ValueError(f"{obj} does not contain image content")

    # if isinstance(obj, ipy.Attachment):
    #     return obj.proxy_url

    # if obj.thumbnail:
    #     return obj.thumbnail.proxy_url or obj.thumbnail.url

    return obj.url


async def get_image_metadata(url: str) -> tuple[ImageType, int]:
    """Uses the headers of the given image url to get the content type and length of the image.

    Raises `ValueError` if the given URL does not have appropriate content headers for an image."""

    async with aiohttp.request("GET", url) as res:
        content_type = res.headers.get("Content-Type")
        content_length = res.headers.get("Content-Length")

        logger.debug(f"Actual {content_type=}, {content_length=}")

        try:
            return ImageType(content_type), int(content_length)
        except ValueError as e:
            raise ValueError("Invalid image metadata for the given URL") from e
