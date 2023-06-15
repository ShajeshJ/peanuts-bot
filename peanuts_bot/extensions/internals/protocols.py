from typing import Protocol, runtime_checkable
import interactions as ipy


@runtime_checkable
class HelpCmdProto(Protocol):
    @staticmethod
    def get_help_color() -> ipy.Color:
        ...
