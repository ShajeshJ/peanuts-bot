from typing import Annotated
import interactions as ipy
import interactions.ext.enhanced as ipye
from config import CONFIG
from peanuts_bot.errors import global_error_handler

bot = ipy.Client(CONFIG.BOT_TOKEN, intents=ipy.Intents.ALL)

# Load library extensions
bot.load("interactions.ext.enhanced")
bot.load("peanuts_bot.middleware.error_handling")

# Apply error handling middleware
bot.event(global_error_handler, name="on_command_error")
bot.event(global_error_handler, name="on_component_error")
bot.event(global_error_handler, name="on_modal_error")

reloadable_extensions = [
    ipy.Choice(name="Role Commands", value="peanuts_bot.extensions.roles"),
    ipy.Choice(name="Channel Commands", value="peanuts_bot.extensions.channels"),
    ipy.Choice(name="Emoji Commands", value="peanuts_bot.extensions.emojis"),
    ipy.Choice(name="RNG Commands", value="peanuts_bot.extensions.rng"),
    ipy.Choice(name="User Commands", value="peanuts_bot.extensions.users"),
    ipy.Choice(name="Message Commands", value="peanuts_bot.extensions.messages"),
]

# Load bot extensions
for ext in reloadable_extensions:
    bot.load(ext.value)


if CONFIG.IS_LOCAL:

    @bot.command(default_member_permissions=ipy.Permissions.ADMINISTRATOR)
    @ipye.setup_options
    async def reload(
        ctx: ipy.CommandContext,
        ext: Annotated[
            str,
            ipye.EnhancedOption(
                str,
                description="The extension to reload",
                choices=reloadable_extensions,
            ),
        ],
    ):
        """[ADMIN-ONLY] Reload bot commands"""
        bot.reload(ext, remove_commands=False)
        await ctx.send(f"{ext} reloaded", ephemeral=True)
