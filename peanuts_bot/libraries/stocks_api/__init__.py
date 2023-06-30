from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Iterable
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
class DailyStock:
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

    @staticmethod
    def from_api(d: dict[str, dict]) -> "DailyStock":
        try:
            meta = d["Meta Data"]
            symbol = meta["2. Symbol"].upper()
            last_refresh = datetime.fromisoformat(meta["3. Last Refreshed"])
            datapoints = [
                DailyPrice(
                    date=datetime.fromisoformat(k),
                    open=float(v["1. open"]),
                    high=float(v["2. high"]),
                    low=float(v["3. low"]),
                    close=float(v["4. close"]),
                )
                for k, v in d["Time Series (Daily)"].items()
            ]
            datapoints.sort(key=lambda dp: dp.date)

            return DailyStock(
                symbol=symbol, refreshed_at=last_refresh, daily_prices=datapoints
            )
        except Exception as e:
            raise ValueError(f"could not parse daily stock api response") from e


@dataclass
class SymbolSearchResult:
    symbol: str
    name: str
    type: str
    match_score: float

    @staticmethod
    def from_api(d: dict[str, str]) -> "SymbolSearchResult":
        try:
            return SymbolSearchResult(
                symbol=d["1. symbol"],
                name=d["2. name"],
                type=d["3. type"],
                match_score=float(d["9. matchScore"]),
            )
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"could not parse symbol search api response") from e


@alru_cache
async def get_daily_stock(symbol: str) -> DailyStock | None:
    """
    Retrieves daily stock information for the specified security

    :param symbol: the ticker symbol
    :return: the daily stock information
    """
    try:
        resp = await _call_stocks_api("TIME_SERIES_DAILY_ADJUSTED", symbol=symbol)
    except StocksAPIRateLimitError:
        logger.warning(
            "TIME_SERIES_DAILY_ADJUSTED stock api rate limit exceeded", exc_info=True
        )
        raise BotUsageError(
            "Rate limited reached for stock data API. Try again in a few minutes."
        )
    except StocksAPIError:
        logger.warning("TIME_SERIES_DAILY_ADJUSTED stock api failed", exc_info=True)
        return None

    return DailyStock.from_api(resp)


@alru_cache
async def search_symbol(search: str) -> list[SymbolSearchResult]:
    """
    Searches for a ticker symbol

    :param search: the search term
    :return: a list of ticker symbols
    """
    try:
        resp = await _call_stocks_api("SYMBOL_SEARCH", keywords=search)
    except StocksAPIError:
        logger.warning("SYMBOL_SEARCH stock api failed", exc_info=True)
        return []

    matches = resp.get("bestMatches")
    if not isinstance(matches, list):
        raise ValueError(f"could not parse symbol search api response {resp}")

    search_results = [SymbolSearchResult.from_api(d) for d in matches]
    search_results = [r for r in search_results if r.type.lower() == "equity"]
    search_results.sort(key=lambda r: r.match_score, reverse=True)
    return search_results


async def _call_stocks_api(f: str, /, **kwargs) -> dict:
    """
    Calls the given stocks api

    :param f: the stock api function to call
    :param kwargs: the arguments to pass to the function
    :return: the json response
    """
    if not isinstance(CONFIG, ALPHAV_CONNECTED):
        raise RuntimeError("stocks api is not connected")

    kwargs["apikey"] = CONFIG.ALPHAV_KEY
    kwargs["function"] = f
    async with aiohttp.ClientSession() as session:
        async with session.get(CONFIG.ALPHAV_API_URL, params=kwargs) as resp:
            data = await resp.json()

            """Alphavantage API always returns 200 with no response header convention
            even on a failure. Unfortunately, the only way to detect failure is to look
            for certain keys in the response body"""
            if "Note" in data:
                raise StocksAPIRateLimitError(data["Note"])
            elif "Error Message" in data:
                raise StocksAPIError(data["Error Message"])

            return data
