import typedenv

from peanuts_bot.libraries.rcon import RconConnection

__all__ = ["CONFIG"]


class EnvConfig(typedenv.EnvLoader, singleton=True):
    ENV: str
    """The env the bot is running on"""
    HEALTH_PROBE: bool = False
    """When True, the bot will expose a ping HTTP endpoint for health checks"""
    BOT_TOKEN: str
    """Auth token for the Discord bot"""
    LOG_LEVEL: str = "INFO"
    """The logging level for the bot"""
    GUILD_ID: int
    """The guild ID for the main guild the bot serves"""
    ADMIN_USER_ID: int
    """The ID of the admin user who manages the bot"""
    LEAGUE_ROLE_ID: int | None
    """The ID of the league mention role"""
    MC_SERVER_IP: str | None
    """The IP address of the Minecraft server"""
    MC_TS_HOST: str | None
    """The Tailscale host address for the Minecraft server"""
    MC_RCON_PASSWORD: str | None
    """The RCON password for the Minecraft server"""
    MC_RCON_PORT: int = 25575
    """The RCON port for the Minecraft server (defaults to 25575)"""

    ALPHAV_API_URL: str | None
    """The Base URL for the alphavantage.co API"""
    ALPHAV_KEY: str | None
    """The API key for the alphavantage.co API"""
    MSH_API_URL: str | None
    """The Base URL for the market.sh API"""
    MSH_API_TOKEN: str | None
    """The API token for the market.sh API"""

    @property
    def IS_LOCAL(self) -> bool:
        """True if the bot is running locally; False otherwise"""
        return self.ENV == "local"

    @property
    def IS_DEBUG(self) -> bool:
        """True if the bot is running in debug mode; False otherwise"""
        return self.LOG_LEVEL == "DEBUG"


class ALPHAV_CONNECTED(EnvConfig, singleton=True):
    ALPHAV_API_URL: str
    ALPHAV_KEY: str


class MC_CONFIG(EnvConfig, singleton=True):
    MC_SERVER_IP: str
    MC_TS_HOST: str
    MC_RCON_PASSWORD: str

    @property
    def rcon(self) -> RconConnection:
        """RCON connection details derived from MC env config."""
        return RconConnection(
            host=self.MC_TS_HOST,
            port=self.MC_RCON_PORT,
            password=self.MC_RCON_PASSWORD,
        )


CONFIG = EnvConfig()
