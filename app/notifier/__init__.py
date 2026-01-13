from app.config import settings
from .base import Notifier

def build_notifier() -> Notifier:
    n = settings.notifier

    if n == "ntfy":
        from .ntfy import NtfyNotifier
        return NtfyNotifier(settings.ntfy_base_url, settings.ntfy_topic)

    if n == "telegram":
        from .telegram import TelegramNotifier
        return TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)

    if n == "discord":
        from .discord import DiscordNotifier
        return DiscordNotifier(settings.discord_webhook_url)

    if n == "slack":
        from .slack import SlackNotifier
        return SlackNotifier(settings.slack_webhook_url)

    raise ValueError(f"Unknown NOTIFIER: {settings.notifier}")
