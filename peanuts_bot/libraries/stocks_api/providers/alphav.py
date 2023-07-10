from dataclasses import dataclass
from datetime import datetime
import logging

import aiohttp
from peanuts_bot.config import ALPHAV_CONNECTED, CONFIG
from peanuts_bot.libraries.stocks_api.errors import (
    StocksAPIError,
    StocksAPIRateLimitError,
)
from peanuts_bot.libraries.stocks_api.interface import (
    IDaily,
    IStock,
    IStockProvider,
    ITicker,
    TimeFilter,
)


logger = logging.getLogger(__name__)


@dataclass
class _TickerResultAV(ITicker):
    type: str
    """the type of security"""


@dataclass
class _DailyPriceAV(IDaily):
    open: float
    """the opening price at the start of the day"""

    high: float
    """the highest price during the day"""

    low: float
    """the lowest price during the day"""


@dataclass
class _StockHistoryAV(IStock[_DailyPriceAV]):
    def get_summary(self) -> list[tuple[str, str]]:
        return super().get_summary() + [
            ("Open", f"{self.today.open:.2f}"),
            ("Day's Range", f"{self.today.low:.2f} - {self.today.high:.2f}"),
        ]


class AlphaV(IStockProvider[_StockHistoryAV, _TickerResultAV]):
    """api wrapper for the AlphaVantage API"""

    @staticmethod
    async def search_symbol(query: str) -> list[_TickerResultAV]:
        resp = await _call_stocks_api("SYMBOL_SEARCH", keywords=query)

        matches = resp.get("bestMatches")
        if not isinstance(matches, list):
            raise StocksAPIError(f"could not parse symbol search api response {resp}")

        search_results = [_parse_symbol_result(d) for d in matches]
        search_results = [r for r in search_results if r.type.lower() == "equity"]
        return search_results

    @staticmethod
    async def get_stock(ticker: str, filter: TimeFilter) -> _StockHistoryAV:
        resp = await _call_stocks_api("TIME_SERIES_DAILY_ADJUSTED", symbol=ticker)
        stock = _parse_stock_api_result(resp)

        max_date = datetime.now()
        min_date = max_date - filter.value
        stock.daily_prices = [
            dp for dp in stock.daily_prices if min_date <= dp.date <= max_date
        ]
        return stock


def _parse_symbol_result(d: dict[str, str]) -> _TickerResultAV:
    """converts a single item from the symbol search the api response to a object"""
    try:
        return _TickerResultAV(
            symbol=d["1. symbol"],
            name=d["2. name"],
            relevance=float(d["9. matchScore"]),
            type=d["3. type"],
        )
    except (KeyError, ValueError, TypeError) as e:
        raise StocksAPIError(f"could not parse symbol search api response") from e


def _parse_stock_api_result(d: dict[str, dict]) -> _StockHistoryAV:
    """parses the stock history from the given api response"""
    try:
        meta = d["Meta Data"]
        symbol = meta["2. Symbol"].upper()
        last_refresh = datetime.fromisoformat(meta["3. Last Refreshed"])
        datapoints = [
            _DailyPriceAV(
                date=datetime.fromisoformat(k),
                close=float(v["4. close"]),
                open=float(v["1. open"]),
                high=float(v["2. high"]),
                low=float(v["3. low"]),
            )
            for k, v in d["Time Series (Daily)"].items()
        ]

        return _StockHistoryAV(
            symbol=symbol, refreshed_at=last_refresh, daily_prices=datapoints
        )
    except Exception as e:
        raise StocksAPIError(f"could not parse daily stock api response") from e


async def _call_stocks_api(f: str, /, **kwargs) -> dict:
    """
    Calls the given stocks api

    :param f: the stock api function to call
    :param kwargs: the arguments to pass to the function
    :return: the json response
    """
    if not isinstance(CONFIG, ALPHAV_CONNECTED):
        raise StocksAPIError("stocks api is not connected")

    kwargs["apikey"] = CONFIG.ALPHAV_KEY
    kwargs["function"] = f
    async with aiohttp.ClientSession() as session:
        async with session.get(CONFIG.ALPHAV_API_URL, params=kwargs) as resp:
            data = await resp.json()

            """Alphavantage API always returns 200 with no response header convention
            even on a failure. Unfortunately, the only way to detect failure is to look
            for certain keys in the response body"""
            if "Note" in data:
                logger.warning(f"{f} failed due to rate limiting")
                raise StocksAPIRateLimitError(data["Note"])
            elif "Error Message" in data:
                logger.warning(f"{f} stock api failed")
                raise StocksAPIError(data["Error Message"])

            return data
