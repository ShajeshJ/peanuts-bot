import interactions as ipy
from config import CONFIG
from peanuts_bot.extensions import ALL_EXTENSIONS

# from peanuts_bot.errors import global_error_handler

# # Load library extensions
# bot.load_extension("peanuts_bot.middleware.error_handling")

# # Apply error handling middleware
# bot.event(global_error_handler, name="on_command_error")
# bot.event(global_error_handler, name="on_component_error")
# bot.event(global_error_handler, name="on_modal_error")


bot = ipy.Client(
    token=CONFIG.BOT_TOKEN,
    intents=ipy.Intents.ALL,
    debug_scope=CONFIG.GUILD_ID,
    delete_unused_application_cmds=True,
)

# Load bot extensions
for ext in ALL_EXTENSIONS:
    bot.load_extension(ext.value)
