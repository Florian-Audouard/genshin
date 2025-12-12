import os
import requests
from dotenv import load_dotenv

load_dotenv()

UID = os.getenv("UID")
L_UID = os.getenv("L_UID")
L_TOKEN = os.getenv("L_TOKEN")

# ✅ Correct URL for global servers
URL = "https://hk4e-api-os.mihoyo.com/ysulog/api/getPrimogemLog"

params = {}

headers = {
    "Cookie": f"ltuid={L_UID}; ltoken={L_TOKEN}; account_id={L_UID};",
    "x-rpc-app_version": "2.34.1",
    "x-rpc-client_type": "5",
    "User-Agent": "Mozilla/5.0",
}

resp = requests.get(URL, headers=headers, params=params)

print("Status:", resp.status_code)
print(resp.text)

if resp.status_code == 200:
    data = resp.json()
    if "data" in data:
        month_data = data["data"].get("month_data", {})
        primos = month_data.get("current_primogems")
        crystals = month_data.get("current_genesis_crystals")
        print(f"Current Primogems: {primos}")
        print(f"Current Genesis Crystals: {crystals}")
