import interactions as ipy
import interactions.ext.enhanced as ipye
from config import CONFIG
from errors import global_error_handler

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
]

# Load bot extensions
for ext in reloadable_extensions:
    bot.load(ext.value)


if CONFIG.IS_LOCAL:

    @bot.command()
    @ipye.setup_options
    async def reload(
        ctx: ipy.CommandContext,
        ext: ipye.EnhancedOption(
            str, description="The extension to reload", choices=reloadable_extensions
        ),
    ):
        """Reload bot commands"""
        if ctx.author.id != CONFIG.ADMIN_USER_ID:
            return

        bot.reload(ext, remove_commands=False)
        await ctx.send(f"{ext} reloaded", ephemeral=True)
