import logging
import types
import typing as t
import interactions as ipy

logger = logging.getLogger(__name__)


def create_component(super_component: t.Callable):
    def component(
        self: ipy.Client,
        *args,
        **kwargs,
    ) -> t.Callable[[t.Coroutine], t.Coroutine]:

        # `super_component` is already bounded to the `Client` object,
        # and client will be passed in as first arg to this function,
        # since it will be bounded to the client. Therefore, we skip
        # passing in self
        super_decorator = super_component(*args, **kwargs)

        def decorator(
            coro: t.Callable[..., t.Coroutine]
        ) -> t.Callable[..., t.Coroutine]:
            async def coro_with_errors(*args, **kwargs):
                combined_args = [*args, *kwargs.values()]
                ctx = next(
                    (a for a in combined_args if isinstance(a, ipy.ComponentContext)),
                    None,
                )

                try:
                    await coro(*args, **kwargs)
                except:
                    print("MADE IT HERE THO?")
                    if ctx:
                        await ctx.send("WE MADE IT BOYYYSS", ephemeral=True)
                    raise

            return super_decorator(coro_with_errors)

        return decorator

    return component


class ErrorHandler(ipy.Extension):
    """
    This is the core of this middle, initialized when loading the extension.

    Improves component error handling by adding enabling a global error handler

    ```py
    # main.py
    client.load("peanuts_bot.middleware.error_handling", ...)  # optional args/kwargs
    ```

    Parameters:

    * `(?)bot: Client`: The client instance. Not required if using `client.load("interactions.ext.enhanced", ...)`.
    """

    def __init__(self, bot: ipy.Client):
        if not isinstance(bot, ipy.Client):
            logger.critical("The bot is not an instance of Client")
            raise TypeError(f"{bot.__class__.__name__} is not interactions.Client!")

        logger.debug("The bot is an instance of Client")

        logger.debug("Modifying component callbacks (modify_callbacks)")
        updated_component = create_component(bot.component)
        bot.component = types.MethodType(updated_component, bot)

        # logger.debug("Modifying modal callbacks (modify_callbacks)")
        # bot.modal = types.MethodType(modal, bot)

        logger.info("Hooks applied")


def setup(bot: ipy.Client) -> ErrorHandler:
    """
    Setup for this extension / middleware
    """
    logger.info("Setting up Better Error Handler")
    return ErrorHandler(bot)
