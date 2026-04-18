from typing import Protocol, runtime_checkable

import discord


@runtime_checkable
class HelpCmdProto(Protocol):
    @staticmethod
    def get_help_color() -> discord.Color: ...
