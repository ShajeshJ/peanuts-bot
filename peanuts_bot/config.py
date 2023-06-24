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
    BOT_TOKEN: str
    """Auth token for the Discord bot"""
    LOG_LEVEL: str = "INFO"
    """The logging level for the bot"""
    GUILD_ID: int
    """The guild ID for the main guild the bot serves"""
    ADMIN_USER_ID: int
    """The ID of the admin user who manages the bot"""

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

    @property
    def IS_ALPHAV_CONNECTED(self) -> bool:
        """True if the bot is connected to the alphavantage.co API; False otherwise"""
        return bool(self.ALPHAV_API_URL) and bool(self.ALPHAV_KEY)

    @property
    def IS_MSH_CONNECTED(self) -> bool:
        """True if the bot is connected to the market.sh API; False otherwise"""
        return bool(self.MSH_API_URL) and bool(self.MSH_API_TOKEN)


CONFIG = EnvConfig()
