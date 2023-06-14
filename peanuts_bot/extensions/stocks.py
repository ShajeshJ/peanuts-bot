from typing import Annotated
import interactions as ipy

from config import CONFIG
from peanuts_bot.libraries import stocks_api


class StocksExtension(ipy.Extension):
    @ipy.slash_command(scopes=[CONFIG.GUILD_ID])
    async def stock(
        self,
        ctx: ipy.SlashContext,
        ticker: Annotated[
            str,
            ipy.slash_str_option(
                description="The ticker symbol to look up",
                required=True,
                autocomplete=True,
            ),
        ],
    ):
        """
        Retrieves daily stock information for the specified security
        """
        stock = await stocks_api.get_daily_stock(ticker)
        await ctx.send(f"{stock.symbol=}, {stock.datapoints[-1]=}")

    @stock.autocomplete("ticker")
    async def stock_ticker_autocomplete(self, ctx: ipy.AutocompleteContext):
        """
        Autocompletes ticker symbol input
        """
        if not ctx.input_text:
            return

        def _get_option_label(r: stocks_api.SymbolSearchResult) -> str:
            label = f"({r.symbol}) {r.name}"
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
