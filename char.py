import requests
import json
from config import ltuid, ltoken, region, uid, username
import requests

BASE_URL = "https://enka.network/"

URL = f"{BASE_URL}api/uid/{uid}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
}
res = requests.get(URL, headers=headers)
res.raise_for_status()
data = res.json()
if "error" not in data:
    first_char = data["avatarInfoList"][0]
    for char_key in first_char:
        print(f"{char_key}, {first_char[char_key]}")