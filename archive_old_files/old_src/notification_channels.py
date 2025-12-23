"""
قنوات التنبيهات: بريد إلكتروني، تيليجرام، وWebhook عام.
"""
from __future__ import annotations

import logging
import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


class EmailNotifier:
    def __init__(self, smtp_server: str, smtp_port: int, sender: str, username: Optional[str] = None, password: Optional[str] = None, use_tls: bool = True) -> None:
        self.smtp_server = smtp_server
        self.smtp_port = int(smtp_port)
        self.sender = sender
        self.username = username or sender
        self.password = password or ""
        self.use_tls = use_tls

    def send(self, subject: str, body: str, recipients: List[str], html: bool = False, attachments: Optional[List[str]] = None) -> bool:
        try:
            if not recipients:
                return False
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.sender
            msg["To"] = ", ".join(recipients)
            if html:
                msg.add_alternative(body, subtype="html")
            else:
                msg.set_content(body)
            for att in attachments or []:
                p = Path(att)
                if not p.exists():
                    continue
                data = p.read_bytes()
                ctype, enc = mimetypes.guess_type(p.name)
                maintype, subtype = (ctype.split("/", 1) if ctype else ("application", "octet-stream"))
                msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=p.name)
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=15) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.exception("Email send failed: %s", e)
            return False


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_ids: List[int]) -> None:
        self.bot_token = bot_token
        self.chat_ids = chat_ids
        self.base = f"https://api.telegram.org/bot{self.bot_token}"

    def send_text(self, text: str) -> bool:
        ok = True
        for cid in self.chat_ids:
            try:
                r = requests.post(self.base + "/sendMessage", json={"chat_id": cid, "text": text})
                ok = ok and r.ok
            except Exception as e:
                logger.warning("Telegram send failed: %s", e)
                ok = False
        return ok

    def send_photo(self, photo_path: str, caption: str = "") -> bool:
        ok = True
        for cid in self.chat_ids:
            try:
                with open(photo_path, "rb") as f:
                    r = requests.post(self.base + "/sendPhoto", data={"chat_id": cid, "caption": caption}, files={"photo": f})
                    ok = ok and r.ok
            except Exception as e:
                logger.warning("Telegram photo failed: %s", e)
                ok = False
        return ok


class WebhookNotifier:
    def __init__(self, url: str, headers: Optional[dict] = None) -> None:
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}

    def post(self, payload: dict) -> bool:
        try:
            r = requests.post(self.url, json=payload, headers=self.headers, timeout=10)
            return r.ok
        except Exception as e:
            logger.warning("Webhook failed: %s", e)
            return False
