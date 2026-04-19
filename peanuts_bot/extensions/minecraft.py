import asyncio
import enum
import logging
import shlex
from typing import Literal

import aiohttp
import async_lru
import discord
from discord import app_commands
from discord.ext import commands
import mcstatus
from mcstatus.status_response import JavaStatusResponse

from peanuts_bot.config import MC_CONFIG
from peanuts_bot.errors import BotUsageError
from peanuts_bot.libraries.discord.admin import send_error_to_admin
from peanuts_bot.libraries.image import decode_b64_image

__all__ = ["MinecraftExtension"]

logger = logging.getLogger(__name__)

CONFIG = MC_CONFIG()


class _SENTINEL(enum.Enum):
    _UNKNOWN = 0


_UNKNOWN = _SENTINEL._UNKNOWN

_mc_group = app_commands.Group(
    name="minecraft", description="Minecraft server commands"
)


class MinecraftExtension(commands.Cog):
    @staticmethod
    def get_help_color() -> discord.Color:
        return discord.Color.from_str("#2ECC71")


@_mc_group.command(name="status")
async def mc_status(interaction: discord.Interaction) -> None:
    """Get the info and status of the Peanuts Minecraft server"""

    status: Literal[_SENTINEL._UNKNOWN] | JavaStatusResponse | None = _UNKNOWN
    try:
        server = await mcstatus.JavaServer.async_lookup(CONFIG.MC_SERVER_IP)
        status = await server.async_status()
    except (ConnectionRefusedError, OSError):
        status = None
    except Exception as e:
        logger.exception("unknown error while getting server status")
        await send_error_to_admin(e, interaction.client)

    server_address_field = (
        "Server Address",
        f"```\n{CONFIG.MC_SERVER_IP}```",
    )

    if status is None:
        embed = discord.Embed(title="Peanuts Server Info", color=discord.Color.red())
        embed.add_field(
            name=server_address_field[0], value=server_address_field[1], inline=False
        )
        embed.add_field(name="Status", value="🔴 Offline", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if status is _UNKNOWN:
        embed = discord.Embed(
            title="Peanuts Server Info",
            description="Error getting server status",
            color=discord.Color(0),
        )
        embed.add_field(
            name=server_address_field[0], value=server_address_field[1], inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(
        title="Peanuts Server Info",
        description=status.description,
        color=discord.Color.green(),
    )
    embed.add_field(
        name=server_address_field[0], value=server_address_field[1], inline=False
    )
    embed.add_field(name="Status", value="🟢 Online", inline=True)
    embed.add_field(
        name="Players",
        value=f"{status.players.online}/{status.players.max}",
        inline=True,
    )
    embed.set_footer(text=f"Running version {status.version.name}")

    if status.icon:
        icon_file = decode_b64_image(status.icon, filename="server-icon.png")
        embed.set_thumbnail(url="attachment://server-icon.png")
        await interaction.response.send_message(
            embed=embed, file=icon_file, ephemeral=True
        )
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)


@_mc_group.command(name="link")
@app_commands.describe(username="Minecraft in-game username")
async def mc_link(interaction: discord.Interaction, username: str) -> None:
    """Whitelist your Minecraft account on the Peanuts server"""

    mc_username = await get_minecraft_user(username)
    if mc_username is None:
        raise BotUsageError(f"User **{username}** not found")

    if not (await _whitelist_user(mc_username, "add")):
        raise BotUsageError("Failed to whitelist user")

    await interaction.response.send_message(
        f"Added **{mc_username}** to the Peanuts server whitelist"
    )


@_mc_group.command(name="unlink")
@app_commands.describe(username="Minecraft in-game username")
async def mc_unlink(interaction: discord.Interaction, username: str) -> None:
    """Remove your Minecraft account from the Peanuts server whitelist"""

    mc_username = await get_minecraft_user(username)
    if mc_username is None:
        raise BotUsageError(f"User **{username}** not found")

    if not (await _whitelist_user(mc_username, "remove")):
        raise BotUsageError("Failed to remove user from whitelist")

    await interaction.response.send_message(
        f"Removed **{mc_username}** from the Peanuts server whitelist"
    )


@async_lru.alru_cache(ttl=5 * 60)
async def get_minecraft_user(name: str) -> str | None:
    """Returns the proper name for a Minecraft user, or None if not found"""

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.mojang.com/users/profiles/minecraft/{name}"
        ) as resp:
            if resp.status >= 400:
                return None

            data = await resp.json()
            return data.get("name", None)


async def _whitelist_user(username: str, operation: Literal["add", "remove"]) -> bool:
    """Whitelist a user on the Minecraft server"""

    logger.info(f"whitelisting user {shlex.quote(username)}")

    proc = await asyncio.create_subprocess_shell(
        " ".join(
            [
                "tailscale",
                "ssh",
                f"{CONFIG.MC_TS_HOST}",
                "'/usr/bin/screen",
                "-S",
                "mc-peanuts",
                "-X",
                "stuff",
                '"/whitelist',
                f"{shlex.quote(operation)}",
                f"{shlex.quote(username)}\n\"'",
            ]
        )
    )

    _, err = await proc.communicate()

    return not err


async def setup(bot: commands.Bot) -> None:
    bot.tree.add_command(_mc_group)
    await bot.add_cog(MinecraftExtension())
