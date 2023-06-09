import interactions as ipy
from config import CONFIG
from peanuts_bot.extensions import ALL_EXTENSIONS

from peanuts_bot.errors import on_error


bot = ipy.Client(
    token=CONFIG.BOT_TOKEN,
    intents=ipy.Intents.ALL,
    debug_scope=CONFIG.GUILD_ID,
    delete_unused_application_cmds=True,
    send_command_tracebacks=False,
)

bot.add_listener(on_error)

# Load bot extensions
for ext in ALL_EXTENSIONS:
    bot.load_extension(ext.value)
