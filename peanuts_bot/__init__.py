import interactions as dpyi
from config import CONFIG

bot = dpyi.Client(CONFIG.BOT_TOKEN)

# Load library extensions
bot.load("interactions.ext.enhanced")
