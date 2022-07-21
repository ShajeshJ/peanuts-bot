import os
import logging
import types
import inspect

logger = logging.getLogger(__name__)

__all__ = ["CONFIG"]

class EnvConfig:
    """
    INSTRUCTIONS:

    To add an environment variable to the config, name the config constant
    the same as the env variable, and include type annotations

    To add properties computed off of env variables, define an @property function
    """

    BOT_TOKEN: str
    LOG_LEVEL: str = "INFO"

    @property
    def IS_DEBUG(self) -> bool:
        return self.LOG_LEVEL == "DEBUG"

    def __init__(self) -> None:
        self.__load_env__()

    def __load_env__(self) -> None:
        """
        The special sauce function, which dynamically imports environment
        variable values into this object, ensuring casting and defaults are
        applied appropriately 
        """
        if getattr(self, "__load_env_called__", False):
            return

        self.__load_env_called__ = True

        for env_name, t_annotation in inspect.get_annotations(type(self)).items():
            logger.debug(f"Retrieving env var {env_name}")
            is_optional = False
            env_type = t_annotation

            # Checks type hinting of the form "<class> | None"
            if (
                isinstance(t_annotation, types.UnionType)
                and len(t_annotation.__args__) == 2
                and t_annotation.__args__[-1] is types.NoneType
            ):
                is_optional = True
                env_type = t_annotation.__args__[0]

            # Supporting easy to cast primitive types to simplify our lives
            if env_type not in [str, int, bool]:
                raise TypeError(f"Unsupported type '{t_annotation}' for env var {env_name}")

            try:
                default = getattr(self, env_name)
                logger.debug(f"Default available for env var {env_name}")
            except AttributeError:
                default = None

            env_value = os.environ.get(env_name, default)
            
            if env_value is None and not is_optional:
                raise KeyError(f"Missing required env var {env_name}")

            if env_value is not None:
                logger.debug(f"Setting env var {env_name}")
                try:
                    env_value = env_type(env_value)
                except ValueError:
                    raise ValueError(f"Cannot cast env var {env_name} to {env_type}")

            setattr(self, env_name, env_value)

CONFIG = EnvConfig()
