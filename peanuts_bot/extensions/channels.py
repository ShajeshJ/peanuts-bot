import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from peanuts_bot.errors import BotUsageError

__all__ = ["ChannelExtension"]

logger = logging.getLogger(__name__)

_channel_group = app_commands.Group(
    name="channel", description="Channel management commands"
)


@_channel_group.command(name="create")
@app_commands.describe(
    name="The name of the new channel",
    category="Category to nest the channel under",
)
async def _channel_create(
    interaction: discord.Interaction,
    name: str,
    category: Optional[discord.CategoryChannel] = None,
) -> None:
    """Create a new text channel"""

    if not interaction.guild:
        raise BotUsageError("This command can only be used in a server")

    existing_channel = next(
        (
            c
            for c in await interaction.guild.fetch_channels()
            if not isinstance(c, discord.CategoryChannel) and c.name == name
        ),
        None,
    )
    if existing_channel:
        raise BotUsageError(f"{existing_channel.mention} already exists")

    channel = await interaction.guild.create_text_channel(
        name=name,
        category=category,
        reason=f"Created by {interaction.user.display_name} via bot commands",
    )
    await interaction.response.send_message(f"Created new channel {channel.mention}")


class ChannelExtension(commands.Cog):
    @staticmethod
    def get_help_color() -> discord.Color:
        return discord.Color.from_str("#3498DB")

    # Voice event listeners (announce_user_join, announce_user_move, bot_leave)
    # are restored in Step 7 once libraries/discord/voice.py is migrated.


async def setup(bot: commands.Bot) -> None:
    bot.tree.add_command(_channel_group)
    await bot.add_cog(ChannelExtension())
