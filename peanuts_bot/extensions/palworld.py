from dataclasses import dataclass
import logging
from typing import Any

from dateutil.relativedelta import relativedelta
import discord
from discord.ext import commands

from peanuts_bot.config import PAL_CONFIG
from peanuts_bot.errors import BotUsageError
from peanuts_bot.libraries.dtutils import format_relativedelta

__all__ = ["PalWorldExtension"]

logger = logging.getLogger(__name__)

CONFIG = PAL_CONFIG()


@dataclass
class ServerInfo:
    version: str
    server_name: str
    fps_avg: float
    current_players: int
    frame_time_ms: float
    max_players: int
    uptime_sec: int
    num_base_camps: int
    in_game_days: int


class PalWorldExtension(commands.Cog):
    _pal_group = discord.app_commands.Group(
        name="palworld", description="PalWorld server commands"
    )

    @staticmethod
    def get_help_color() -> discord.Color:
        return discord.Color.from_str("#76d1e7")

    @_pal_group.command(name="stats")
    async def palworld_stats(self, interaction: discord.Interaction) -> None:
        """Get the info and servers stats for Peanuts' PalWorld server"""
        await interaction.response.defer(ephemeral=True)

        try:
            async with CONFIG.session as pal_session:
                async with pal_session.get("/v1/api/info") as response:
                    response.raise_for_status()
                    basic_info: dict[str, Any] = await response.json()

                async with pal_session.get("/v1/api/metrics") as response:
                    response.raise_for_status()
                    server_stats: dict[str, Any] = await response.json()

            stats = ServerInfo(
                version=basic_info["version"],
                server_name=basic_info["servername"],
                fps_avg=server_stats["serverfpsaverage"],
                current_players=server_stats["currentplayernum"],
                frame_time_ms=server_stats["serverframetime"],
                max_players=server_stats["maxplayernum"],
                uptime_sec=server_stats["uptime"],
                num_base_camps=server_stats["basecampnum"],
                in_game_days=server_stats["days"],
            )
        except:
            logger.warning("failed to get palworld server info", exc_info=True)
            raise BotUsageError(
                "Could not get server info. The server may be down or unreachable. Try again later."
            )

        description = None
        if CONFIG.PAL_SERVER_CONNECT_IP:
            description = (
                f"Server Connection IP:\n```\n{CONFIG.PAL_SERVER_CONNECT_IP}```\n"
            )
            if CONFIG.PAL_SERVER_CONNECT_PW:
                description += f"Server Connection Password:\n```\n{CONFIG.PAL_SERVER_CONNECT_PW}```\n───"

        embed = discord.Embed(
            title=f"{stats.server_name} — Server Stats",
            description=description,
            color=self.get_help_color(),
        )

        embed.add_field(name="Version", value=stats.version, inline=True)
        embed.add_field(name="Average FPS", value=f"{stats.fps_avg:.2f}", inline=True)
        embed.add_field(
            name="Frame Time",
            value=f"{stats.frame_time_ms:.3f} ms",
            inline=True,
        )

        embed.add_field(
            name="Players Online", value=f"{stats.current_players}/{stats.max_players}"
        )
        embed.add_field(name="In-Game Days", value=stats.in_game_days, inline=True)
        embed.add_field(name="# of Base Camps", value=stats.num_base_camps, inline=True)

        relative_uptime = relativedelta(seconds=stats.uptime_sec)
        embed.set_footer(
            text=f"Server has been online for {format_relativedelta(relative_uptime)}"
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @_pal_group.command(name="save")
    async def palworld_save(self, interaction: discord.Interaction) -> None:
        """Trigger a manual save on Peanuts' PalWorld server"""
        await interaction.response.defer()

        try:
            async with CONFIG.session as pal_session:
                async with pal_session.post("/v1/api/save") as response:
                    response.raise_for_status()
        except:
            logger.warning("failed to trigger palworld server save", exc_info=True)
            raise BotUsageError("Manual save failed. Try again later.")

        await interaction.followup.send("💾 Server world has saved successfully.")

    @_pal_group.command(name="restart")
    @discord.app_commands.describe(
        delay="Delay in seconds before restarting the server",
        message="System message to send before restarting the server. Use '@delay' to substitute the delay value",
    )
    async def palworld_restart(
        self,
        interaction: discord.Interaction,
        delay: int = 10,
        message: str = "Server shutting down to update in @delay seconds...",
    ) -> None:
        """Restart Peanuts' PalWorld server. If needed, save first to avoid losing progress."""
        await interaction.response.defer()

        try:
            message = message.replace("@delay", str(delay))
            async with CONFIG.session as pal_session:
                async with pal_session.post(
                    "/v1/api/shutdown", json={"waittime": delay, "message": message}
                ) as response:
                    response.raise_for_status()
        except:
            logger.warning("failed to trigger palworld server restart", exc_info=True)
            raise BotUsageError("Server restart failed. Try again later.")

        await interaction.followup.send(f"🔄 Server will restart in {delay} seconds.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PalWorldExtension())
