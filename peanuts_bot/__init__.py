import interactions as ipy
from config import CONFIG

bot = ipy.Client(CONFIG.BOT_TOKEN)

# Load library extensions
bot.load("interactions.ext.enhanced")
