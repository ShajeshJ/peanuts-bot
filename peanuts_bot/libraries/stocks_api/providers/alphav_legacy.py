from dataclasses import dataclass
from datetime import datetime
import logging
import aiohttp
from async_lru import alru_cache
from peanuts_bot.config import ALPHAV_CONNECTED, CONFIG
from peanuts_bot.errors import BotUsageError

from peanuts_bot.libraries.stocks_api.errors import (
    StocksAPIError,
    StocksAPIRateLimitError,
)

logger = logging.getLogger(__name__)


@dataclass
class DailyPrice:
    date: datetime
    """the date the prices were recorded"""

    close: float
    """the closing price at the end of the day"""

    open: float | None = None
    """the opening price at the start of the day"""

    high: float | None = None
    """the highest price during the day"""

    low: float | None = None
    """the lowest price during the day"""


@dataclass
class StockHistory:
    """Represents daily stock information"""

    symbol: str
    """the ticker symbol"""

    refreshed_at: datetime
    """the last time the data was refreshed"""

    daily_prices: list[DailyPrice]
    """the daily datapoints, sorted by ascending date"""

    @property
    def today(self) -> DailyPrice:
        """the latest daily price (usually the current day)"""
        if not self.daily_prices:
            raise AttributeError("daily price is not available")

        return self.daily_prices[-1]

    @property
    def yesterday(self) -> DailyPrice:
        """the second latest daily price (usually the previous day)"""
        if len(self.daily_prices) < 2:
            raise AttributeError("yesterday's daily price is not available")

        return self.daily_prices[-2]


@dataclass
class TickerSymbol:
    symbol: str
    name: str
    type: str
    match_score: float
