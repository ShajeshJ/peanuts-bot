from dataclasses import dataclass
from datetime import datetime
import aiohttp

from config import CONFIG


def is_stocks_api_connected() -> bool:
    """
    Checks if the stocks api is connected

    :return: True if connected, False otherwise
    """
    return bool(CONFIG.STOCKS_API_KEY) and bool(CONFIG.STOCKS_API_URL)


@dataclass
class DailyDP:
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class DailyStock:
    symbol: str
    last_refresh: datetime
    datapoints: list[DailyDP]

    @staticmethod
    def from_api(d: dict[str, dict]) -> "DailyStock":
        try:
            meta = d["Meta Data"]
            symbol = meta["2. Symbol"].upper()
            last_refresh = datetime.fromisoformat(meta["3. Last Refreshed"])
            datapoints = [
                DailyDP(
                    date=datetime.fromisoformat(k),
                    open=float(v["1. open"]),
                    high=float(v["2. high"]),
                    low=float(v["3. low"]),
                    close=float(v["4. close"]),
                    volume=int(v["6. volume"]),
                )
                for k, v in d["Time Series (Daily)"].items()
            ]
            datapoints.sort(key=lambda dp: dp.date)

            return DailyStock(
                symbol=symbol, last_refresh=last_refresh, datapoints=datapoints
            )
        except Exception as e:
            raise ValueError(f"could not parse daily stock api response") from e


async def get_daily_stock(symbol: str) -> DailyStock:
    """
    Retrieves daily stock information for the specified security

    :param symbol: the ticker symbol
    :return: the daily stock information
    """
    resp = await _call_stocks_api("TIME_SERIES_DAILY_ADJUSTED", symbol=symbol)
    if "Meta Data" not in resp:
        raise ValueError(f"could not parse daily stock api response {resp}")

    return DailyStock.from_api(resp)


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


async def search_symbol(search: str) -> list[SymbolSearchResult]:
    """
    Searches for a ticker symbol

    :param search: the search term
    :return: a list of ticker symbols
    """
    resp = await _call_stocks_api("SYMBOL_SEARCH", keywords=search)

    matches = resp.get("bestMatches")
    if not isinstance(matches, list):
        raise ValueError(f"could not parse symbol search api response {resp}")

    search_results = [SymbolSearchResult.from_api(d) for d in matches]
    search_results.sort(key=lambda r: r.match_score, reverse=True)
    return search_results


async def _call_stocks_api(f: str, /, **kwargs) -> dict:
    """
    Calls the given stocks api

    :param f: the stock api function to call
    :param kwargs: the arguments to pass to the function
    :return: the json response
    """
    if not is_stocks_api_connected():
        raise RuntimeError("stocks api is not connected")

    kwargs["apikey"] = CONFIG.STOCKS_API_KEY
    kwargs["function"] = f
    async with aiohttp.ClientSession() as session:
        async with session.get(CONFIG.STOCKS_API_URL, params=kwargs) as resp:
            return await resp.json()
