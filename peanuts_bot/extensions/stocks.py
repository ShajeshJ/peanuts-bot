from typing import Annotated
import interactions as ipy

from config import CONFIG
from peanuts_bot.errors import BotUsageError
from peanuts_bot.libraries import stocks_api


class StocksExtension(ipy.Extension):
    @ipy.slash_command(scopes=[CONFIG.GUILD_ID])
    async def stock(
        self,
        ctx: ipy.SlashContext,
        ticker: Annotated[
            str,
            ipy.slash_str_option(
                description="**Warning: autocomplete is api rate limited**. The ticker symbol to look up",
                required=True,
                autocomplete=True,
            ),
        ],
    ):
        """
        Retrieves daily stock information for the specified security
        """
        stock = await stocks_api.get_daily_stock(ticker)

        if not stock:
            raise BotUsageError(
                f"Could not get stock info for {ticker}. Try again later."
            )

        if not stock.datapoints:
            raise BotUsageError(f"no daily datapoints available for {ticker}")

        await ctx.send("", embed=daily_stock_to_embed(stock))

    @stock.autocomplete("ticker")
    async def stock_ticker_autocomplete(self, ctx: ipy.AutocompleteContext):
        """
        Autocompletes ticker symbol input
        """
        if not ctx.input_text:
            return

        def _get_option_label(r: stocks_api.SymbolSearchResult) -> str:
            label = f"{r.symbol} ({r.name})"
            if len(label) > 100:
                label = label[:97] + "..."
            return label

        search_results = await stocks_api.search_symbol(ctx.input_text)
        await ctx.send(
            [
                ipy.SlashCommandChoice(name=_get_option_label(r), value=r.symbol)
                for r in search_results
            ]
        )


def daily_stock_to_embed(stock: stocks_api.DailyStock) -> ipy.Embed:
    """
    Parse daily stock data into an informational embed

    :param stock: the daily stock data
    :return: the embed
    """
    embed = _create_embed(stock=stock)
    embed = _add_description(embed, stock=stock)
    embed = _add_fields(embed, stock=stock)

    return embed


def _create_embed(*, stock: stocks_api.DailyStock) -> ipy.Embed:
    """
    Creates an embed for the stock data
    """
    return ipy.Embed(
        title=f"__{stock.symbol}__ Stock Info (Daily)",
        url=f"https://ca.finance.yahoo.com/quote/{stock.symbol}",
        color=ipy.Color.from_hex("#8935d9"),
        footer=ipy.EmbedFooter(text=f"Last refreshed {stock.last_refresh.date()}"),
    )


def _add_description(embed: ipy.Embed, /, *, stock: stocks_api.DailyStock) -> ipy.Embed:
    """
    Adds the description to the embed
    """
    if not stock.has_multiple_days:
        embed.description = "**```diff\nData for yesterady unavailable```**"
    else:
        today = stock.datapoints[-1]
        yesterday = stock.datapoints[-2]

        # Calculate close difference
        diff = today.close - yesterday.close
        diff_percent = diff / yesterday.close * 100

        # Format close difference; for negative values, the sign will already included in `diff`
        diff_sign = "+" if diff >= 0 else ""
        embed.description = (
            f"**```diff\n{diff_sign}{diff:.2f} ({diff_sign}{diff_percent:.2f}%)```**"
        )

    return embed


def _add_fields(embed: ipy.Embed, /, *, stock: stocks_api.DailyStock) -> ipy.Embed:
    """
    Adds the fields to the embed
    """
    today = stock.datapoints[-1]
    all_fields = [
        ipy.EmbedField("Close", f"{today.close:.2f}", inline=True),
        ipy.EmbedField("Open", f"{today.open:.2f}", inline=True),
        ipy.EmbedField(
            "Day's Range", f"{today.low:.2f} - {today.high:.2f}", inline=True
        ),
    ]

    if stock.has_multiple_days:
        yesterday = stock.datapoints[-2]
        all_fields.insert(
            1, ipy.EmbedField("Previous Close", f"{yesterday.close:.2f}", inline=True)
        )

    embed.add_fields(*all_fields)

    return embed
