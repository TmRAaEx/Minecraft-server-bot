import asyncio
from Bot import DiscordBot

if __name__ == "__main__":
    bot = DiscordBot()
    asyncio.run(bot.run())
