import logging

import discord

from config import Config
from logging_config import configure_logging

logger = logging.getLogger("discord-presence")


class PresenceClient(discord.Client):
    async def on_ready(self):
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"slot ĐRL • quét mỗi {Config.CHECK_INTERVAL}s",
            ),
        )
        logger.info("Discord bot online")


if __name__ == "__main__":
    configure_logging()
    if not Config.DISCORD_BOT_TOKEN:
        raise SystemExit("Thiếu DISCORD_BOT_TOKEN")
    client = PresenceClient(intents=discord.Intents.none())
    client.run(Config.DISCORD_BOT_TOKEN, log_handler=None)
