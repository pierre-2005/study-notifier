import requests
from .base import Notifier

class NtfyNotifier(Notifier):
    def __init__(self, base_url: str, topic: str):
        if not topic:
            raise ValueError("NTFY_TOPIC is required for ntfy notifier")
        self.url = f"{base_url.rstrip('/')}/{topic}"

    def send(self, title: str, message: str) -> None:
        # ntfy supports publishing via simple HTTP POST with the body as message. :contentReference[oaicite:11]{index=11}
        headers = {"Title": title}
        r = requests.post(self.url, data=message.encode("utf-8"), headers=headers, timeout=10)
        r.raise_for_status()
