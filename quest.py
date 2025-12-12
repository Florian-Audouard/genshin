import hashlib
import random
import string
import time
import requests
import json
from config import ltuid, ltoken, region, uid

def generate_ds():
    salt = "6s25p5ox5y14umn1p61aqyyvbvvl3lrt"
    t = str(int(time.time()))
    r = ''.join(random.choice(string.ascii_letters) for _ in range(6))
    raw = f"salt={salt}&t={t}&r={r}"
    h = hashlib.md5(raw.encode()).hexdigest()
    return f"{t},{r},{h}"

headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "x-rpc-app_version": "1.5.0",
    "x-rpc-client_type": "5",
    "x-rpc-language": "en-us",
    "Cookie": f"ltoken_v2={ltoken}; ltuid_v2={ltuid};",
    # "DS": generate_ds(),
}

payload = {
    "role_id": uid,
    "server": region
}

url = "https://bbs-api-os.hoyolab.com/game_record/genshin/api/character"

print("Fetching character list...")
res = requests.post(url, headers=headers, data=json.dumps(payload))
res.raise_for_status()
data = res.json()

if data.get("retcode") == 0:
    chars = data["data"]["avatars"]
    for c in chars:
        print(c["name"], c["level"], c["rarity"])
else:
    print(data)
