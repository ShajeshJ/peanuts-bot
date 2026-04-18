# `libraries/stocks_api/` — Stock Data Abstraction

Provider-agnostic stock API layer. Only loaded when `CONFIG.ALPHAV_CONNECTED` config guard passes (raises `ValueError` if unconfigured).

**Usage pattern:**
```python
from peanuts_bot.libraries.stocks_api import StockAPI, AlphaV
api = StockAPI(AlphaV)
tickers = await api.search_symbol("AAPL")
stock = await api.get_stock("AAPL", TimeFilter.LAST_MONTH)
```

---

## `errors.py`

- `StocksAPIError` — base exception for all stock API failures
- `StocksAPIRateLimitError(StocksAPIError)` — raised when Alpha Vantage rate-limits the request

---

## `interface.py` — Abstract interfaces & `StockAPI` wrapper

**Data interfaces** (all are `@dataclass + ABC`):
- `ITicker` — ticker search result: `symbol_id`, `symbol`, `name`, `relevance`
- `IDaily` — single day's prices: `date`, `close`
- `IStock[TDaily]` — historical prices: `symbol`, `refreshed_at`, `daily_prices` (sorted ascending); `.today` / `.yesterday` convenience properties; `get_summary()` returns `list[tuple[str, str]]` for embed display

**`TimeFilter(relativedelta, Enum)`** — `LAST_WEEK`, `LAST_MONTH`, `LAST_3_MONTHS`; passed to `get_stock` to window the returned history.

**`IStockProvider[TStock, TTicker]`** — abstract base for provider implementations; requires `search_symbol(query)` and `get_stock(ticker, filter)` as static abstract methods.

**`StockAPI[TStock, TTicker]`** — thin wrapper around a provider class (not instance). Adds 5-minute `alru_cache` to both `search_symbol` and `get_stock`. Sort is applied here (tickers by relevance desc, daily prices by date asc).

---

## `providers/alphav.py` — Alpha Vantage implementation

**`AlphaV(IStockProvider)`** — concrete provider. Reads config via `ALPHAV_CONNECTED()` at module import time (so this module must not be imported unless the guard passes).

Key implementation details:
- Alpha Vantage **always returns HTTP 200**, even on failure. Errors are detected by checking the response body for `"Note"` (rate limit) or `"Error Message"` (API error).
- `get_stock` fetches full history then **filters client-side** by date range using `TimeFilter`.
- `search_symbol` filters results to `type == "equity"` only.
- `_redact_errors(d)` recursively replaces `ALPHAV_KEY` in error responses before logging.
- Concrete data types: `_TickerResultAV` (adds `type`), `_DailyPriceAV` (adds `open`, `high`, `low`), `_StockHistoryAV` (extends `get_summary` with open/range).

---

## `__init__.py`

Re-exports `AlphaV` and `StockAPI` — the only public surface callers need.
