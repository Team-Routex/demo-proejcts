import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE = {
    "ENGINE": os.getenv("DB_ENGINE", "postgresql"),
    "HOST": os.getenv("DB_HOST", "127.0.0.1"),
    "PORT": int(os.getenv("DB_PORT", 5432)),
    "USER": os.getenv("DB_USER", "energy-pros"),
    "PASSWORD": os.getenv("DB_PASSWORD", "energy-pros"),
    "NAME": os.getenv("DB_NAME", "raft_blog"),
}

MEDIA_ROOT = str(BASE_DIR / "uploads")
MEDIA_URL = "/uploads/"

APPS = ["models"]


