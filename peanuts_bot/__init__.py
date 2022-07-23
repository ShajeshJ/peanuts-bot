import interactions as ipy
from config import CONFIG

bot = ipy.Client(CONFIG.BOT_TOKEN, intents=ipy.Intents.ALL)

# Load library extensions
bot.load("interactions.ext.enhanced")

# Load bot extensions
bot.load("peanuts_bot.extensions.roles")
