import os
import logging
import inspect
import typing as t

from peanuts_bot.libraries.types_ext import get_optional_subtype


logger = logging.getLogger(__name__)


class EnvLoader:
    __loader_locked__ = False

    def __init__(self) -> None:
        self.__load_env__()

    def __load_env__(self) -> None:
        """
        The special sauce function, which dynamically imports environment
        variable values into this object, ensuring casting and defaults are
        applied appropriately 
        """
        if self.__loader_locked__:
            return

        for env_name, t_annotation in inspect.get_annotations(type(self)).items():
            logger.debug(f"Retrieving env var {env_name}")
            is_optional = False
            env_type = t_annotation

            try:
                env_type = get_optional_subtype(t_annotation)
                logger.debug(f"<{env_type}> found as optional annotation's subtype")
            except ValueError:
                logger.debug(f"<{t_annotation}> found as non-optional type")

            # Limiting casting to easy-to-cast primitives to simplify my life
            if env_type not in [str, int, bool]:
                raise TypeError(f"Unsupported type <{t_annotation}> for env var {env_name}")

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

        self.__loader_locked__ = True

    def __setattr__(self, __name: str, __value: t.Any) -> None:
        if self.__loader_locked__:
            raise AttributeError(f"Failed to set attribute '{__name}'. Assignment frozen for {type(self)} object")

        return super().__setattr__(__name, __value)
