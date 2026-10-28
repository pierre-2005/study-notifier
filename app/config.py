from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass(frozen=True)
class Settings:
    notifier: str = os.getenv("NOTIFIER", "ntfy").strip().lower()
    timezone: str = os.getenv("TIMEZONE", "America/Edmonton").strip()

    ntfy_base_url: str = os.getenv("NTFY_BASE_URL", "https://ntfy.sh").strip().rstrip("/")
    ntfy_topic: str = os.getenv("NTFY_TOPIC", "").strip()

settings = Settings()
