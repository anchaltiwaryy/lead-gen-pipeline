"""Real-time alerting & workflow notification webhook module."""
import os
import json
import urllib.request
from logger import log

WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")


def send_alert(title: str, message: str, fields: dict | None = None, is_error: bool = False) -> bool:
    """Send an alert to a configured webhook (Slack, Discord, Telegram) or log to stdout."""
    log_level = log.error if is_error else log.info
    log_level(f"[ALERT] {title}: {message} | Details: {fields}")

    if not WEBHOOK_URL:
        return False

    try:
        # Standard webhook payload
        payload = {
            "title": f"🚨 {title}" if is_error else f"🤖 {title}",
            "text": message,
            "details": fields or {},
        }
        
        # Support Discord webhook formatting
        if "discord.com" in WEBHOOK_URL:
            embed_fields = [{"name": k, "value": str(v), "inline": True} for k, v in (fields or {}).items()]
            payload = {
                "embeds": [{
                    "title": f"🚨 {title}" if is_error else f"🤖 {title}",
                    "description": message,
                    "color": 15158332 if is_error else 3066993,
                    "fields": embed_fields,
                }]
            }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Pipeline-Notifier/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        log.warning(f"[notify] Failed to dispatch webhook alert: {e}")
        return False
