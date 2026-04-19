# `libraries/image.py` — Image Utilities

General-purpose image helpers used across extensions (notably `emojis.py`). No matplotlib — the TODO description was inaccurate.

---

**`ImageSize(int)`** — `int` subclass with `.kb`, `.mb`, `.gb` properties and a human-readable `__str__` (e.g. `"256 KB"`).

**`MAX_EMOJI_FILE_SIZE`** — `ImageSize(256 * 1024)` — Discord's emoji upload size limit.

**`ImageType(str, Enum)`** — MIME type enum: `JPEG`, `PNG`, `GIF`, `WEBP`, `OTHER`. `.extension` property returns the file extension (e.g. `".png"`).

**`is_image(obj: Attachment | Embed) -> bool`**
Returns True if the object's URL ends with a known image extension, or if it has an image content type (attachments) / embed type (embeds).

**`get_image_url(obj: Attachment | Embed) -> str | None`**
Returns `obj.url` if it passes `is_image`, otherwise `None`.

**`decode_b64_image(image: str, *, filename=None) -> discord.File`**
Decodes a base64 image string (strips `data:image/...` prefix if present) into a `discord.File` backed by `io.BytesIO`. Pair with `embed.set_thumbnail(url="attachment://{filename}")` to embed in-memory images.

**`get_image_metadata(url: str) -> tuple[ImageType, int]`**
Async. GETs the URL and reads `Content-Length` + MIME type from the response. Returns `(ImageType, size_in_bytes)`. Raises `ValueError` if content headers are missing or MIME is not an image type.
