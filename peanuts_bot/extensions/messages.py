from typing import Annotated
import interactions as ipy
import interactions.ext.enhanced as ipye

from config import CONFIG

__all__ = ["setup", "MessagesExtension"]


class MessagesExtension(ipy.Extension):
    def __init__(self, client: ipy.Client) -> None:
        self.client: ipy.Client = client

    @ipy.extension_command(
        scope=CONFIG.GUILD_ID, default_member_permissions=ipy.Permissions.ADMINISTRATOR
    )
    @ipye.setup_options
    async def speak(
        self,
        ctx: ipy.CommandContext,
        message: Annotated[
            str,
            ipye.EnhancedOption(str, description="The message for the bot to repeat"),
        ],
    ):
        """[ADMIN-ONLY] Make the bot say something"""
        await ctx.send(message)

    @ipy.extension_command(
        scope=CONFIG.GUILD_ID, default_member_permissions=ipy.Permissions.ADMINISTRATOR
    )
    async def messages(self, _: ipy.CommandContext):
        pass

    @messages.subcommand()
    @ipye.setup_options
    async def delete(
        self,
        ctx: ipy.CommandContext,
        amount: Annotated[
            int,
            ipye.EnhancedOption(
                int,
                description="**Caution against > 100**. The number of messages to delete.",
                min_value=1,
            ),
        ] = 1,
    ):
        """[ADMIN-ONLY] Deletes the last X messages in the channel"""

        await ctx.defer(ephemeral=True)
        # TODO: Need to find out why bulk=True doesn't work
        msgs = await ctx.channel.purge(amount, bulk=False)
        await ctx.send(f"Deleted {len(msgs)} message(s)", ephemeral=True)


def setup(client: ipy.Client):
    MessagesExtension(client)
