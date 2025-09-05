import io
from typing import Annotated
import interactions as ipy
import matplotlib
import matplotlib.pyplot as plt

from peanuts_bot.config import CONFIG
from peanuts_bot.errors import BotUsageError
from peanuts_bot.libraries.stocks_api import StockAPI, AlphaV
from peanuts_bot.libraries.stocks_api.errors import StocksAPIRateLimitError
from peanuts_bot.libraries.stocks_api.interface import IDaily, IStock, ITicker

__all__ = ["StockExtension"]


class StockExtension(ipy.Extension):
    @staticmethod
    def get_help_color() -> ipy.Color:
        return ipy.FlatUIColors.WISTERIA

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
        """Retrieves daily stock information for the specified security"""

        stock_api = StockAPI(AlphaV)

        try:
            stock = await stock_api.get_stock(ticker)
        except StocksAPIRateLimitError:
            raise BotUsageError(
                f"Could not get stock info for {ticker}. Try again later."
            )

        graph_file = _gen_stock_graph(stock)

        await ctx.send(
            "", file=graph_file, embed=daily_stock_to_embed(stock, graph=graph_file)
        )

    @stock.autocomplete("ticker")
    async def stock_ticker_autocomplete(self, ctx: ipy.AutocompleteContext):
        """
        Autocompletes ticker symbol input
        """
        if not ctx.input_text:
            return

        def _get_option_label(r: ITicker) -> str:
            label = f"{r.symbol} ({r.name})"
            if len(label) > 100:
                label = label[:97] + "..."
            return label

        stock_api = StockAPI(AlphaV)

        search_results = await stock_api.search_symbol(ctx.input_text)
        await ctx.send(
            [
                ipy.SlashCommandChoice(name=_get_option_label(r), value=r.symbol_id)
                for r in search_results
            ]
        )


def daily_stock_to_embed(
    stock: IStock[IDaily], *, graph: ipy.File | None = None
) -> ipy.Embed:
    """
    Parse daily stock data into an informational embed

    :param stock: the daily stock data
    :return: the embed
    """
    embed = _create_embed(stock=stock)
    embed = _add_description(embed, stock=stock)
    embed = _add_fields(embed, stock=stock)

    if graph:
        embed.set_image(url=f"attachment://{graph.file_name}")

    return embed


def _create_embed(*, stock: IStock[IDaily]) -> ipy.Embed:
    """
    Creates an embed for the stock data
    """
    return ipy.Embed(
        title=f"__{stock.symbol}__ Stock Info (Daily)",
        url=f"https://ca.finance.yahoo.com/quote/{stock.symbol}",
        color=ipy.Color.from_hex("#8935d9"),
        footer=ipy.EmbedFooter(text=f"Last refreshed {stock.refreshed_at.date()}"),
    )


def _add_description(embed: ipy.Embed, /, *, stock: IStock[IDaily]) -> ipy.Embed:
    """
    Adds the description to the embed
    """
    try:
        today, yesterday = stock.today, stock.yesterday
    except AttributeError:
        embed.description = "**```diff\nData for yesterady unavailable```**"
        return embed

    # Calculate close difference
    diff = today.close - yesterday.close
    diff_percent = diff / yesterday.close * 100

    # Format close difference; for negative values, the sign will already included in `diff`
    diff_sign = "+" if diff >= 0 else ""
    embed.description = (
        f"**```diff\n{diff_sign}{diff:.2f} ({diff_sign}{diff_percent:.2f}%)```**"
    )

    return embed


def _add_fields(embed: ipy.Embed, /, *, stock: IStock[IDaily]) -> ipy.Embed:
    """
    Adds the fields to the embed
    """
    all_fields = [
        ipy.EmbedField(name, value, inline=True) for name, value in stock.get_summary()
    ]
    embed.add_fields(*all_fields)

    return embed


def _gen_stock_graph(stock: IStock[IDaily]) -> ipy.File | None:
    """
    Generates a graph of the historical stock data
    """
    if len(stock.daily_prices) < 2:
        return None

    matplotlib.use("agg")

    plt.figure(figsize=(15, 10), dpi=40)
    x = [dp.date.strftime("%y/%m/%d") for dp in stock.daily_prices]
    y = [dp.close for dp in stock.daily_prices]
    plt.plot(x, y, color="tab:red")

    plt.xticks(fontsize=24, rotation=45)
    plt.yticks(fontsize=24)

    plt.grid(axis="both", alpha=1)
    plt.gca().spines["top"].set_alpha(0.0)
    plt.gca().spines["bottom"].set_alpha(0.0)
    plt.gca().spines["right"].set_alpha(0.0)
    plt.gca().spines["left"].set_alpha(0.0)

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format="png", bbox_inches="tight")
    img_buffer.seek(0)

    plt.close("all")

    return ipy.File(img_buffer, file_name="stockgraph.png")
