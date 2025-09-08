import interactions as ipy
from peanuts_bot.config import CONFIG
from peanuts_bot.extensions import ALL_EXTENSIONS

from peanuts_bot.errors import on_error
from peanuts_bot.extensions.internals import REQUIRED_EXTENSION_PROTOS
from peanuts_bot.libraries.discord.voice import BotVoice, announcer_rejoin_on_startup


bot = ipy.Client(
    token=CONFIG.BOT_TOKEN,
    intents=ipy.Intents.ALL,
    debug_scope=CONFIG.GUILD_ID,
    delete_unused_application_cmds=True,
    send_command_tracebacks=False,
    activity=ipy.Activity.create("/help", type=ipy.ActivityType.WATCHING),
)

bot.add_listener(on_error)
bot.add_listener(announcer_rejoin_on_startup)
BotVoice.init(bot)

# Load bot extensions
for ext_info in ALL_EXTENSIONS:
    bot.load_extension(ext_info.module_path)

for proto in REQUIRED_EXTENSION_PROTOS:
    for ext in bot.ext.values():
        if not isinstance(ext, proto):
            raise RuntimeError(f"{ext.__name__} does not implement {proto.__name__}")
