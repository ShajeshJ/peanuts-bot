from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


class TimeWindow(relativedelta, Enum):
    WEEK = relativedelta(weeks=1)
    MONTH = relativedelta(months=1)
    THREE_MONTHS = relativedelta(months=3)

    def __add__(self, other):
        return self.value.__add__(other)

    def __radd__(self, other):
        return self.value.__radd__(other)

    def __sub__(self, other):
        return self.value.__sub__(other)

    def __rsub__(self, other):
        return self.value.__rsub__(other)


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
