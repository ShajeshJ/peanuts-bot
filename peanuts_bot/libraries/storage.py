from __future__ import annotations
from typing import TypeVar

__all__ = ["get", "put", "pop"]

_VT = TypeVar("_VT")

_STORAGE: dict[str, _VT] = {}


def get(key) -> _VT | None:
    """
    GETs the value stored under the given key.

    :param key: The lookup key for the stored value
    :return: The value stored, or `None` if the key was not found
    """

    return _STORAGE.get(key)


def put(key: str, value: _VT):
    """
    PUTs the given data into storage under the given key.

    :param key: The lookup key for the given value
    :param value: The value to be stored
    """
    if value is None:
        raise ValueError(f"Cannot store a value of `None`")

    _STORAGE[key] = value


def pop(key: str) -> _VT:
    """
    Pops the key out of storage and and returns its value

    :param key: The lookup key for the stored value
    :return: The value stored, or `None` if the key was not found
    """

    return _STORAGE.pop(key, None)
