import os
from dotenv import load_dotenv

# === Load credentials from .env ===
load_dotenv()

uid = os.getenv("UID")        # Your in-game UID
ltuid = os.getenv("L_UID")    # ltuid
ltoken = os.getenv("L_TOKEN")  # ltoken
region = os.getenv("REGION", "os_euro")  # default to Europe server
username = os.getenv("USERNAME")  # Optional: your username