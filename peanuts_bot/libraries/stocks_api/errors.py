class StocksAPIError(Exception):
    pass


class StocksAPIRateLimitError(StocksAPIError):
    pass
