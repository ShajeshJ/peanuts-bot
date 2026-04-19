import io

import discord
from discord import app_commands
from discord.ext import commands
import matplotlib
import matplotlib.pyplot as plt

from peanuts_bot.errors import BotUsageError
from peanuts_bot.libraries.stocks_api import AlphaV, StockAPI
from peanuts_bot.libraries.stocks_api.errors import StocksAPIRateLimitError
from peanuts_bot.libraries.stocks_api.interface import IDaily, IStock, ITicker

__all__ = ["StockExtension"]


class StockExtension(commands.Cog):
    @staticmethod
    def get_help_color() -> discord.Color:
        return discord.Color.from_str("#8E44AD")

    @app_commands.command(name="stock")
    @app_commands.describe(
        ticker="**Warning: autocomplete is api rate limited**. The ticker symbol to look up"
    )
    async def stock(self, interaction: discord.Interaction, ticker: str) -> None:
        """Retrieves daily stock information for the specified security"""

        stock_api = StockAPI(AlphaV)

        try:
            stock_data = await stock_api.get_stock(ticker)
        except StocksAPIRateLimitError:
            raise BotUsageError(
                f"Could not get stock info for {ticker}. Try again later."
            )

        graph_file = _gen_stock_graph(stock_data)
        embed = daily_stock_to_embed(stock_data, graph=graph_file)

        if graph_file:
            await interaction.response.send_message(embed=embed, file=graph_file)
        else:
            await interaction.response.send_message(embed=embed)

    @stock.autocomplete("ticker")
    async def stock_ticker_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        if not current:
            return []

        def _get_option_label(r: ITicker) -> str:
            label = f"{r.symbol} ({r.name})"
            if len(label) > 100:
                label = label[:97] + "..."
            return label

        stock_api = StockAPI(AlphaV)
        search_results = await stock_api.search_symbol(current)
        return [
            app_commands.Choice(name=_get_option_label(r), value=r.symbol_id)
            for r in search_results
        ]


def daily_stock_to_embed(
    stock: IStock[IDaily], *, graph: discord.File | None = None
) -> discord.Embed:
    embed = _create_embed(stock=stock)
    embed = _add_description(embed, stock=stock)
    embed = _add_fields(embed, stock=stock)

    if graph:
        embed.set_image(url=f"attachment://{graph.filename}")

    return embed


def _create_embed(*, stock: IStock[IDaily]) -> discord.Embed:
    embed = discord.Embed(
        title=f"__{stock.symbol}__ Stock Info (Daily)",
        url=f"https://ca.finance.yahoo.com/quote/{stock.symbol}",
        color=discord.Color.from_str("#8935d9"),
    )
    embed.set_footer(text=f"Last refreshed {stock.refreshed_at.date()}")
    return embed


def _add_description(
    embed: discord.Embed, /, *, stock: IStock[IDaily]
) -> discord.Embed:
    try:
        today, yesterday = stock.today, stock.yesterday
    except AttributeError:
        embed.description = "**```diff\nData for yesterady unavailable```**"
        return embed

    diff = today.close - yesterday.close
    diff_percent = diff / yesterday.close * 100

    diff_sign = "+" if diff >= 0 else ""
    embed.description = (
        f"**```diff\n{diff_sign}{diff:.2f} ({diff_sign}{diff_percent:.2f}%)```**"
    )

    return embed


def _add_fields(embed: discord.Embed, /, *, stock: IStock[IDaily]) -> discord.Embed:
    for name, value in stock.get_summary():
        embed.add_field(name=name, value=value, inline=True)
    return embed


def _gen_stock_graph(stock: IStock[IDaily]) -> discord.File | None:
    if len(stock.daily_prices) < 2:
        return None

    matplotlib.use("agg")

    plt.figure(figsize=(15, 10), dpi=60)
    x = [dp.date.strftime("%Y-%m-%d") for dp in stock.daily_prices]
    y = [dp.close for dp in stock.daily_prices]
    plt.plot(x, y, color="tab:red")

    plt.xticks(fontsize=20, rotation=60)
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

    return discord.File(img_buffer, filename="stockgraph.png")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StockExtension())
