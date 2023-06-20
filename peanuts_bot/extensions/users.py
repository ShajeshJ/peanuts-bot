import logging
import interactions as ipy

from peanuts_bot.config import CONFIG

__all__ = ["UserExtension"]

logger = logging.getLogger(__name__)


_MODIFY_MEMBER_SAFE_ERROR_CODES = [50013]


class UserExtension(ipy.Extension):
    @staticmethod
    def get_help_color() -> ipy.Color:
        return ipy.FlatUIColors.EMERLAND

    @ipy.listen("on_member_update", delay_until_ready=True)
    async def add_username_to_nickname(self, event: ipy.events.MemberUpdate):
        """Updates a user's nickname to ensure that it contains their username"""

        if event.guild_id != CONFIG.GUILD_ID:
            return

        member = event.after
        username, old_nick = member.user.username, member.nick

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
                await member.edit_nickname(None, reason="nickname too long")
            except ipy.errors.HTTPException as e:
                if e.code not in _MODIFY_MEMBER_SAFE_ERROR_CODES:
                    raise
                logger.info(f"failed to reset nickname for '{username}'")
                return

            await member.send(
                f"The nickname, '{old_nick}' is too long! "
                f"Please shorten it to {32 - (len(new_nick) - len(old_nick))} characters or less."
            )
            return

        logger.debug(f"updating nickname for '{old_nick}'")

        try:
            await member.edit_nickname(new_nick, reason="adding username to nickname")
        except ipy.errors.HTTPException as e:
            if e.code not in _MODIFY_MEMBER_SAFE_ERROR_CODES:
                raise
            logger.info(f"failed to reset nickname for '{username}'")
            return

        logger.debug(f"updated nickname to '{member.nickname}'")
