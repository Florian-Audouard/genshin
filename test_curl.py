import hashlib
import random
import string
import time
import requests
from config import *


# Constants
URL_DIARY_DETAIL = "https://sg-hk4e-api.hoyolab.com/event/ysledgeros/month_detail"
month = time.localtime().tm_mon
current_page = 1
type_ = 1
page_size = 100
lang = "en-us"

# DS generator (using hashlib instead of manual MD5)
def generate_ds():
    salt = "6s25p5ox5y14umn1p61aqyyvbvvl3lrt"
    timestamp = int(time.time())
    rand_str = ''.join(random.choice(string.ascii_letters) for _ in range(6))
    raw = f"salt={salt}&t={timestamp}&r={rand_str}"
    hash_val = hashlib.md5(raw.encode()).hexdigest()
    return f"{timestamp},{rand_str},{hash_val}"

# Headers
headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Accept-Encoding": "gzip, deflate, br",
    "sec-ch-ua": '"Chromium";v="112", "Microsoft Edge";v="112", "Not:A-Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.46"
    ),
    "x-rpc-app_version": "1.5.0",
    "x-rpc-client_type": "5",
    "x-rpc-language": lang,
    "Cookie": f"ltoken_v2={ltoken}; ltuid_v2={ltuid};",
    "DS": generate_ds(),
}

# Parameters
params = {
    "region": region,
    "uid": uid,
    "month": month,
    "type": type_,
    "current_page": current_page,
    "page_size": page_size,
    "lang": lang,
}

# Request
try:
    response = requests.get(URL_DIARY_DETAIL, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    
    if "data" in data and "list" in data["data"]:
        diary_list = data["data"]["list"]
        print("Fetched list successfully:")
        for item in diary_list:
            print(item)
    else:
        print("Unexpected response:", data)

except requests.RequestException as e:
    print("Error fetching data:", e)
