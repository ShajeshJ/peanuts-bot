from typing import Protocol, runtime_checkable
from peanuts_bot.libraries.env import EnvLoader

__all__ = ["CONFIG"]


class EnvConfig(EnvLoader):
    """
    INSTRUCTIONS:

    To add an environment variable to the config, name the config constant
    the same as the env variable, and include type annotations

    To add properties computed off of env variables, define an @property function
    """

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


@runtime_checkable
class ALPHAV_CONNECTED(Protocol):
    ALPHAV_API_URL: str
    ALPHAV_KEY: str


CONFIG = EnvConfig()
