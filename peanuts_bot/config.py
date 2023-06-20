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
    BOT_TOKEN: str
    LOG_LEVEL: str = "INFO"
    GUILD_ID: int
    ADMIN_USER_ID: int
    STOCKS_API_URL: str | None
    STOCKS_API_KEY: str | None

    @property
    def IS_LOCAL(self) -> bool:
        return self.ENV == "local"

    @property
    def IS_DEBUG(self) -> bool:
        return self.LOG_LEVEL == "DEBUG"

    @property
    def IS_STOCKS_API_CONNECTED(self) -> bool:
        return bool(self.STOCKS_API_URL) and bool(self.STOCKS_API_KEY)


CONFIG = EnvConfig()
