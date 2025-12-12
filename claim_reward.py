import os
import genshin

from dotenv import load_dotenv
import asyncio

load_dotenv()


UID = os.getenv("UID")
L_UID = os.getenv("L_UID")
L_TOKEN = os.getenv("L_TOKEN")
cookies = {"ltuid_v2": L_UID, "ltoken_v2": L_TOKEN}


async def main():
    client = genshin.Client()
    client.set_cookies(cookies)

    # claim daily reward
    try:
        reward = await client.claim_daily_reward()
    except genshin.AlreadyClaimed:
        print("Daily reward already claimed")
    else:
        print(f"Claimed {reward.amount}x {reward.name}")


if __name__ == "__main__":

    asyncio.run(main())
