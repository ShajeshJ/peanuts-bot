from __future__ import annotations
from typing import Generic, TypeVar

__all__ = ["Storage"]

_VT = TypeVar("_VT")


class Storage(Generic[_VT]):
    def __init__(self) -> None:
        self._store: dict[str, _VT] = {}

    def get(self, key: str) -> _VT | None:
        """
        GETs the value stored under the given key.

        :param key: The lookup key for the stored value
        :return: The value stored, or `None` if the key was not found
        """

        return self._store.get(key)

    def put(self, key: str, value: _VT):
        """
        PUTs the given data into storage under the given key.

        :param key: The lookup key for the given value
        :param value: The value to be stored
        """
        if value is None:
            raise ValueError(f"Cannot store a value of `None`")

        self._store[key] = value

    def pop(self, key: str) -> _VT:
        """
        Pops the key out of storage and and returns its value

        :param key: The lookup key for the stored value
        :return: The value stored, or `None` if the key was not found
        """

        return self._store.pop(key, None)
