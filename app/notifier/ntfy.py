import requests
from .base import Notifier


class NtfyNotifier(Notifier):
    def __init__(self, base_url: str, topic: str):
        if not topic:
            raise ValueError("NTFY_TOPIC is required for ntfy notifier")
        self.url = f"{base_url.rstrip('/')}/{topic}"

    def send(self, title: str, message: str) -> bool:
        headers = {"Title": title}

        try:
            response = requests.post(
                self.url,
                data=message.encode("utf-8"),
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[ntfy] send failed: {e}")
            return False