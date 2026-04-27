import asyncio
import logging
import struct
from dataclasses import dataclass

__all__ = [
    "RconAuthError",
    "RconConnection",
    "RconError",
    "send_rcon_command",
]

logger = logging.getLogger(__name__)

_AUTH = 3
_AUTH_RESPONSE = 2
_EXEC_COMMAND = 2
_RESPONSE_VALUE = 0

_HEADER_STRUCT = struct.Struct("<iii")  # size, id, type
_HEADER_SIZE = _HEADER_STRUCT.size  # 12

_CMD_REQ_ID = 0
_SENTINEL_REQ_ID = 1


@dataclass(frozen=True, slots=True)
class RconConnection:
    """Connection details for an RCON server."""

    host: str
    port: int
    password: str


class RconError(Exception):
    """An RCON request failed (network, protocol, or auth)."""


class RconAuthError(RconError):
    """The server rejected the RCON password."""


async def send_rcon_command(
    conn: RconConnection,
    command: str,
    *,
    timeout: float = 5.0,
) -> str:
    """Connect, authenticate, send one command, and return the full response.

    Handles RCON's split-response protocol transparently, so the caller sees
    one complete response string regardless of how many packets the server
    used to return it.

    :param conn: Server host, port, and password.
    :param command: Command to run, e.g. ``"whitelist add Notch"``.
    :param timeout: Maximum seconds to wait for the whole exchange.
    :raises RconAuthError: If the server rejects the password.
    :raises RconError: For network failures, timeouts, or malformed packets.
    """
    try:
        return await asyncio.wait_for(_run(conn, command), timeout=timeout)
    except asyncio.TimeoutError as e:
        raise RconError(f"rcon timed out after {timeout}s") from e
    except OSError as e:
        raise RconError(f"rcon connection failed: {e}") from e


async def _run(conn: RconConnection, command: str) -> str:
    reader, writer = await asyncio.open_connection(conn.host, conn.port)
    try:
        writer.write(_pack(_CMD_REQ_ID, _AUTH, conn.password))
        await writer.drain()
        auth_id, auth_type, _ = await _read_packet(reader)
        if auth_id == -1:
            raise RconAuthError("rcon auth rejected: bad password")
        if auth_type != _AUTH_RESPONSE:
            raise RconError(f"unexpected packet type during auth: {auth_type}")

        writer.write(_pack(_CMD_REQ_ID, _EXEC_COMMAND, command))
        writer.write(_pack(_SENTINEL_REQ_ID, _EXEC_COMMAND, ""))
        await writer.drain()

        parts: list[str] = []
        while True:
            pid, _, body = await _read_packet(reader)
            if pid == _SENTINEL_REQ_ID:
                break
            if pid == _CMD_REQ_ID:
                parts.append(body)
        return "".join(parts)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            logger.debug("ignored exception while closing rcon socket", exc_info=True)


def _pack(req_id: int, ptype: int, body: str) -> bytes:
    """Build a single RCON packet. Size prefix excludes itself."""
    payload = body.encode("utf-8") + b"\x00\x00"
    size = _HEADER_SIZE - 4 + len(payload)
    return _HEADER_STRUCT.pack(size, req_id, ptype) + payload


async def _read_packet(reader: asyncio.StreamReader) -> tuple[int, int, str]:
    """Read one RCON packet. Returns ``(id, type, body)`` with trailing nulls stripped."""
    size_bytes = await reader.readexactly(4)
    (size,) = struct.unpack("<i", size_bytes)
    if size < 10:
        raise RconError(f"malformed rcon packet: size={size}")
    rest = await reader.readexactly(size)
    req_id, ptype = struct.unpack("<ii", rest[:8])
    if rest[-2:] != b"\x00\x00":
        raise RconError("malformed rcon packet: missing null terminator")
    body = rest[8:-2].decode("utf-8", errors="replace")
    return req_id, ptype, body


# Inline self-checks on _pack — module-level assertions are the project's
# "lightweight inline tests" pattern (see STYLE_GUIDE.md "Libraries").
assert _pack(0, _AUTH, "x") == struct.pack("<iii", 11, 0, _AUTH) + b"x\x00\x00"
assert (
    _pack(1, _EXEC_COMMAND, "")
    == struct.pack("<iii", 10, 1, _EXEC_COMMAND) + b"\x00\x00"
)
