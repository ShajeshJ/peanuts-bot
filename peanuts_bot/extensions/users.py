import logging

import discord
from discord.ext import commands

from peanuts_bot.config import CONFIG

__all__ = ["UserExtension"]

logger = logging.getLogger(__name__)


_MODIFY_MEMBER_SAFE_ERROR_CODES = [50013]


class UserExtension(commands.Cog):
    @staticmethod
    def get_help_color() -> discord.Color:
        return discord.Color.from_str("#1ABC9C")

    @commands.Cog.listener("on_member_update")
    async def add_username_to_nickname(
        self, before: discord.Member, after: discord.Member
    ):
        """Updates a user's nickname to ensure that it contains their username"""

        if after.guild.id != CONFIG.GUILD_ID:
            return

        username, old_nick = after.name, after.nick

        if old_nick is None:
            logger.debug(f"nickname was reset for '{username}'")
            return

        if username in old_nick:
            logger.debug(f"username already contained in nick for '{old_nick}'")
            return

        new_nick = f"{old_nick} [{username}]"
        if len(new_nick) > 32:
            logger.debug(f"new nick '{new_nick}' is too long. resetting...")

            try:
                await after.edit(nick=None, reason="nickname too long")
            except discord.HTTPException as e:
                if e.code not in _MODIFY_MEMBER_SAFE_ERROR_CODES:
                    raise
                logger.info(f"failed to reset nickname for '{username}'")
                return

            await after.send(
                f"The nickname, '{old_nick}' is too long! "
                f"Please shorten it to {32 - (len(new_nick) - len(old_nick))} characters or less."
            )
            return

        logger.debug(f"updating nickname for '{old_nick}'")

        try:
            await after.edit(nick=new_nick, reason="adding username to nickname")
        except discord.HTTPException as e:
            if e.code not in _MODIFY_MEMBER_SAFE_ERROR_CODES:
                raise
            logger.info(f"failed to update nickname for '{username}'")
            return

        logger.debug(f"updated nickname to '{after.nick}'")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UserExtension())
