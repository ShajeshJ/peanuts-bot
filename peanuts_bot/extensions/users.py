import logging
import interactions as ipy

__all__ = ["setup", "UsersExtension"]

logger = logging.getLogger(__name__)


_MODIFY_MEMBER_SAFE_ERROR_CODES = [50013]


class UsersExtension(ipy.Extension):
    def __init__(self, client: ipy.Client) -> None:
        self.client: ipy.Client = client

    @ipy.extension_listener(name="on_raw_guild_member_update")
    async def add_username_to_nickname(self, member: ipy.GuildMember):
        """Updates a user's nickname to ensure that it contains their username"""

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
                member = await member.modify(nick=None)
            except ipy.LibraryException as e:
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
            member = await member.modify(nick=new_nick)
        except ipy.LibraryException as e:
            if e.code not in _MODIFY_MEMBER_SAFE_ERROR_CODES:
                raise
            logger.info(f"failed to reset nickname for '{username}'")
            return

        logger.debug(f"updated nickname to '{member.name}'")


def setup(client: ipy.Client):
    UsersExtension(client)
