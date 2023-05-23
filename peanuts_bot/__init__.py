from typing import Annotated
import interactions as ipy
from config import CONFIG

# from peanuts_bot.errors import global_error_handler

# # Load library extensions
# bot.load_extension("peanuts_bot.middleware.error_handling")

# # Apply error handling middleware
# bot.event(global_error_handler, name="on_command_error")
# bot.event(global_error_handler, name="on_component_error")
# bot.event(global_error_handler, name="on_modal_error")

reloadable_extensions: list[ipy.SlashCommandChoice] = [
    # ipy.SlashCommandChoice(name="Role Commands", value="peanuts_bot.extensions.roles"),
    # ipy.SlashCommandChoice(
    #     name="Channel Commands", value="peanuts_bot.extensions.channels"
    # ),
    # ipy.SlashCommandChoice(
    #     name="Emoji Commands", value="peanuts_bot.extensions.emojis"
    # ),
    # ipy.SlashCommandChoice(name="RNG Commands", value="peanuts_bot.extensions.rng"),
    # ipy.SlashCommandChoice(name="User Commands", value="peanuts_bot.extensions.users"),
    # ipy.SlashCommandChoice(
    #     name="Message Commands", value="peanuts_bot.extensions.messages"
    # ),
]


# if CONFIG.IS_LOCAL:


class PeanutsBot(ipy.Client):
    @ipy.slash_command(
        scopes=[CONFIG.GUILD_ID],
        default_member_permissions=ipy.Permissions.ADMINISTRATOR,
    )
    async def reload(
        self,
        ctx: ipy.SlashContext,
        ext: Annotated[
            str,
            ipy.slash_str_option(
                required=True,
                description="The extension to reload",
                choices=reloadable_extensions,
            ),
        ],
    ):
        """[ADMIN-ONLY] Reload bot commands"""
        # bot.reload_extension(ext)
        await ctx.send(f"{ext} reloaded", ephemeral=True)


bot = PeanutsBot(
    token=CONFIG.BOT_TOKEN, intents=ipy.Intents.ALL, debug_scope=CONFIG.GUILD_ID
)

# Load bot extensions
for ext in reloadable_extensions:
    bot.load_extension(ext.value)
