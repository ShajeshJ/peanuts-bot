from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Generic, Type, TypeVar
from async_lru import alru_cache
from dateutil.relativedelta import relativedelta

from peanuts_bot.libraries.stocks_api.errors import StocksAPIError


TDaily = TypeVar("TDaily", bound="IDaily")
TStock = TypeVar("TStock", bound="IStock")
TTicker = TypeVar("TTicker", bound="ITicker")


class TimeFilter(relativedelta, Enum):
    LAST_WEEK = relativedelta(weeks=1)
    LAST_MONTH = relativedelta(months=1)
    LAST_3_MONTHS = relativedelta(months=3)


@dataclass
class ITicker(ABC):
    """the interface for a ticker found from a ticker search"""

    symbol_id: str
    """the unique id for a ticker in the provider's api"""

    symbol: str
    """the ticker symbol"""

    name: str
    """the name of the company"""

    relevance: float
    """the relevance of the search result"""


@dataclass
class IDaily(ABC):
    """the interface for price information for a single day"""

    date: datetime
    """the date the prices were recorded"""

    close: float
    """the closing price at the end of the day"""


@dataclass
class IStock(Generic[TDaily], ABC):
    """the interface for historical daily prices of a stock"""

    symbol: str
    """the ticker symbol"""

    refreshed_at: datetime
    """the last time the data was refreshed"""

    daily_prices: list[TDaily]
    """the daily datapoints, sorted by ascending date"""

    @property
    def today(self) -> TDaily:
        """the latest daily price (usually the current day)"""
        if not self.daily_prices:
            raise AttributeError("daily price is not available")

        return self.daily_prices[-1]

    @property
    def yesterday(self) -> TDaily:
        """the second latest daily price (usually the previous day)"""
        if len(self.daily_prices) < 2:
            raise AttributeError("yesterday's daily price is not available")

        return self.daily_prices[-2]

    def get_summary(self) -> list[tuple[str, str]]:
        """returns a list of summary fields"""
        summary = [("Close", f"{self.today.close:.2f}")]
        try:
            summary.append(("Previous Close", f"{self.yesterday.close:.2f}"))
        except AttributeError:
            pass
        return summary


class IStockProvider(ABC, Generic[TStock, TTicker]):
    """the interface for a stock API provider"""

    @staticmethod
    @abstractmethod
    async def search_symbol(query: str) -> list[TTicker]:
        """an api call to search for ticker symbols matching the query

        Args:
            query: the query to search with
        Returns:
            a list of matching tickers
        """
        ...

    @staticmethod
    @abstractmethod
    async def get_stock(ticker: str, filter: TimeFilter) -> TStock:
        """an api call to get the stock history for a ticker

        Args:
            ticker: the ticker symbol
            filter: the window of time to apply to retrieved history
        """
        ...


class StockAPI(Generic[TStock, TTicker]):
    def __init__(self, provider: Type[IStockProvider[TStock, TTicker]]):
        self._provider = provider

    async def search_symbol(self, query: str):
        """searches for a ticker symbol matching by either the symbol, or the company

        Args:
            query: the query to search with
        Returns:
            a list of matching tickers, ordered by relevance
        """

        @alru_cache(ttl=5 * 60)
        async def _search(query):
            """wrapped as inner function to perserve doc string"""
            results = await self._provider.search_symbol(query)
            results.sort(key=lambda r: r.relevance, reverse=True)
            return results

        return await _search(query)

    async def get_stock(self, ticker: str, filter: TimeFilter = TimeFilter.LAST_MONTH):
        """gets the stock history for a ticker

        Args:
            ticker: the ticker symbol
            filter: the window of time to apply to retrieved history
        Returns:
            the stock history, sorted by date
        Raises:
            StocksAPIError: if the stock history is not available
        """

        @alru_cache(ttl=5 * 60)
        async def _get_stock(ticker, filter):
            stock = await self._provider.get_stock(ticker, filter)
            stock.daily_prices.sort(key=lambda dp: dp.date)
            if not stock.daily_prices:
                raise StocksAPIError(f"history for {ticker} is not available")
            return stock

        return await _get_stock(ticker, filter)
