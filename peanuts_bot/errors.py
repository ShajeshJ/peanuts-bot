import interactions as ipy

from peanuts_bot.constants.bot import SOMETHING_WRONG


async def global_error_handler(
    ctx: ipy.CommandContext | ipy.ComponentContext, e: Exception
):
    """
    Global error handler for the bot; can be used to handle command and component errors
    """

    await ctx.send(SOMETHING_WRONG, ephemeral=True)

    raise e
