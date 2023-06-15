import interactions as ipy
from config import CONFIG
from peanuts_bot.extensions import ALL_EXTENSIONS

from peanuts_bot.errors import on_error
from peanuts_bot.extensions.internals import REQUIRED_EXTENSION_PROTOS


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
    bot.load_extension(ext.module_path)

for proto in REQUIRED_EXTENSION_PROTOS:
    for ext in bot.ext.values():
        if not isinstance(ext, proto):
            raise RuntimeError(f"{ext.__name__} does not implement {proto.__name__}")
