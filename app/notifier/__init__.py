from app.config import settings
from .base import Notifier
from .ntfy import NtfyNotifier


def build_notifier() -> Notifier:
    notifier_name = (settings.notifier or "ntfy").strip().lower()

    if notifier_name == "ntfy":
        return NtfyNotifier(settings.ntfy_base_url, settings.ntfy_topic)

    raise ValueError(
        f"Unsupported NOTIFIER: {settings.notifier}. "
        "This app currently supports only NOTIFIER=ntfy."
    )