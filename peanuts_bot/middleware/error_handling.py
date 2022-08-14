import logging
import types
import typing as t
import interactions as ipy

logger = logging.getLogger(__name__)


def component_with_error(super_component: t.Callable) -> t.Callable:
    """Creates and returns a component decorator that performs error handling

    :param super_component: The originally bound component decorator method
    :return: An updated component decorator to be bound to the Client object
    """

    def component(
        self: ipy.Client,
        *args,
        **kwargs,
    ) -> t.Callable[[t.Coroutine], t.Coroutine]:

        # This decorator should be bound to the `Client`` object
        # Since `super_component` should already be bound to the
        # same object, we skip passing `self` when calling it
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
                    return await coro(*args, **kwargs)
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
    This is the core of this middleware, initialized when loading the extension.

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
        component_decorator = component_with_error(bot.component)
        bot.component = types.MethodType(component_decorator, bot)

        # logger.debug("Modifying modal callbacks (modify_callbacks)")
        # bot.modal = types.MethodType(modal, bot)

        logger.info("Hooks applied")


def setup(bot: ipy.Client) -> ErrorHandler:
    """
    Setup for this extension / middleware
    """
    logger.info("Setting up Better Error Handler")
    return ErrorHandler(bot)