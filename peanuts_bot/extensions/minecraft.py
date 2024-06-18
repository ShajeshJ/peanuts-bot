import logging
import enum
import aiohttp
import async_lru
import interactions as ipy
import mcstatus
import mcstatus.status_response

from peanuts_bot.config import CONFIG
from peanuts_bot.libraries.discord_bot import send_error_to_admin
from peanuts_bot.libraries.image import decode_b64_image

__all__ = ["MinecraftExtension"]

logger = logging.getLogger(__name__)


class _SENTINEL(enum.Enum):
    _UNKNOWN = 0


_UNKNOWN = _SENTINEL._UNKNOWN


class MinecraftExtension(ipy.Extension):
    @staticmethod
    def get_help_color() -> ipy.Color:
        return ipy.FlatUIColors.EMERLAND

    @ipy.slash_command(scopes=[CONFIG.GUILD_ID])
    async def minecraft(self, _: ipy.SlashContext):
        pass

    @minecraft.subcommand()
    async def status(self, ctx: ipy.SlashContext):
        """Get the info and status of the Peanuts Minecraft server"""

        status = _UNKNOWN
        try:
            server = await mcstatus.JavaServer.async_lookup(CONFIG.MC_SERVER_IP)
            status = await server.async_status()
        except (ConnectionRefusedError, OSError):
            status = None
        except Exception as e:
            logger.exception("unknown error while getting server status")
            await send_error_to_admin(e, ctx.bot)

        embed = ipy.Embed(
            title=f"Peanuts Server Info",
            fields=[
                ipy.EmbedField(
                    "Server Address", f"```\n{CONFIG.MC_SERVER_IP}```", inline=False
                )
            ],
        )

        if status is None:
            embed.color = ipy.BrandColors.RED
            embed.add_field("Status", "🔴 Offline", inline=True)
            await ctx.send(embeds=embed, ephemeral=True)
            return
        elif status is _UNKNOWN:
            embed.description = "Error getting server status"
            embed.color = ipy.BrandColors.BLACK
            await ctx.send(embeds=embed, ephemeral=True)
            return

        embed.color = ipy.BrandColors.GREEN
        embed.description = status.description
        embed.add_field("Status", "🟢 Online", inline=True)
        embed.add_field(
            "Players", f"{status.players.online}/{status.players.max}", inline=True
        )
        embed.set_footer(f"Running version {status.version.name}")

        file = None
        if status.icon:
            file = decode_b64_image(status.icon, filename="server-icon.png")
            embed.set_thumbnail("attachment://server-icon.png")

        await ctx.send(embeds=embed, file=file, ephemeral=True)


@async_lru.alru_cache(ttl=5 * 60)  # 5 min cache
async def get_minecraft_user(name: str) -> str | None:
    """Returns the proper name for a Minecraft user, or None if not found"""

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.mojang.com/users/profiles/minecraft/{name}"
        ) as resp:
            if resp.status >= 400:
                return None

            return (await resp.json()).get("name", None)
