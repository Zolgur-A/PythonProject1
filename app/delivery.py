from __future__ import annotations

import json
import logging
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage

from app.config import EmailSettings, TelegramSettings


LOGGER = logging.getLogger(__name__)
TELEGRAM_SEND_MESSAGE_URL = "https://api.telegram.org/bot{token}/sendMessage"
MESSAGE_PREVIEW_LIMIT = 3500


class TelegramSender:
    def __init__(self, settings: TelegramSettings) -> None:
        self._settings = settings

    def send(self, message: str) -> None:
        if not self._settings.enabled:
            LOGGER.info("Telegram delivery is disabled")
            return
        if not self._settings.bot_token or not self._settings.chat_ids:
            LOGGER.warning("Telegram delivery skipped: token or chat IDs are empty")
            return

        for chat_id in self._settings.chat_ids:
            payload = urllib.parse.urlencode(
                {
                    "chat_id": chat_id,
                    "text": message[:MESSAGE_PREVIEW_LIMIT],
                }
            ).encode("utf-8")
            request = urllib.request.Request(
                TELEGRAM_SEND_MESSAGE_URL.format(token=self._settings.bot_token),
                data=payload,
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                response.read()


class EmailSender:
    def __init__(self, settings: EmailSettings) -> None:
        self._settings = settings

    def send(self, subject: str, body: str) -> None:
        if not self._settings.enabled:
            LOGGER.info("Email delivery is disabled")
            return
        if not self._is_configured():
            LOGGER.warning("Email delivery skipped: SMTP settings are incomplete")
            return

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._settings.from_address
        message["To"] = ", ".join(self._settings.to_addresses)
        message.set_content(body)

        with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(self._settings.username, self._settings.password)
            smtp.send_message(message)

    def _is_configured(self) -> bool:
        required_values = [
            self._settings.smtp_host,
            self._settings.username,
            self._settings.password,
            self._settings.from_address,
        ]
        return all(required_values) and bool(self._settings.to_addresses)


class DeliveryService:
    def __init__(self, telegram: TelegramSender, email: EmailSender) -> None:
        self._telegram = telegram
        self._email = email

    def send_article(self, article_name: str, enriched_article: str) -> None:
        subject = f"Анализ статьи: {article_name}"
        self._telegram.send(enriched_article)
        self._email.send(subject, enriched_article)


def to_pretty_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
