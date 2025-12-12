import os
from dotenv import load_dotenv
import genshinstats as gs
from get_auth_key.get_auth_key import get_auth_key

load_dotenv()


UID = os.getenv("UID")
L_UID = os.getenv("L_UID")
L_TOKEN = os.getenv("L_TOKEN")
auth_key = get_auth_key()

cookies = {"ltuid_v2": L_UID, "ltoken_v2": L_TOKEN}

gs.set_cookie(cookies)
gs.set_authkey(auth_key)

for i in gs.get_primogem_log(size=40):
    print(f"{i['time']} - {i['reason']}: {i['amount']} primogems")
