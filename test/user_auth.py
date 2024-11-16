import asyncio
import time

from discordbot.publicbot import discordAuth


async def test_auth():
    auth = discordAuth("1071161378")
    auth.waiting_users.append({"username": "takechi-scratch", "discord_id": -1, "status": "waiting", "start_time": int(time.time())})
    print(await auth.check_authcode(-1))


asyncio.run(test_auth())
