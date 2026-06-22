import os
import time
from typing import Optional

import requests


TIMEOUT = 30
POLL_INTERVAL = 3
PUBLIC_ACK_MESSAGE = """Build queued successfully.

Your ROM link was received and sent for processing.

Estimated build time: 40-60 minutes.
If another build is already running, your request will wait safely in queue."""

USAGE_MESSAGE = "Usage: /mezo <ROM_LINK>"
PUBLIC_FAILURE_MESSAGE = "Build request could not be submitted. Please contact MEZO."


def get_env(name: str, default: str = "") -> str:
    value = os.environ.get(name, default).strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def is_valid_rom_link(value: str) -> bool:
    value = value.strip()
    return value.startswith(("http://", "https://")) and " " not in value


def send_message(bot_token: str, chat_id: str, text: str, reply_to_message_id: Optional[int] = None) -> None:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json=payload,
        timeout=TIMEOUT,
    )
    response.raise_for_status()


def dispatch_workflow(rom_link: str) -> None:
    token = get_env("GH_WORKFLOW_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY", "mohammedmezo99/mezo_lite").strip()
    workflow_file = os.environ.get("GITHUB_WORKFLOW_FILE", "build.yml").strip()
    ref = os.environ.get("GITHUB_WORKFLOW_REF", "main").strip()

    response = requests.post(
        f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/dispatches",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "ref": ref,
            "inputs": {
                "rom_link": rom_link,
                "request_source": "telegram",
                "publish_release": "true",
            },
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()


def handle_mezo_command(bot_token: str, update: dict, public_chat_id: str) -> None:
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))
    message_id = message.get("message_id")
    text = (message.get("text") or "").strip()

    if chat_id != public_chat_id:
        return

    parts = text.split(maxsplit=1)
    rom_link = parts[1].strip() if len(parts) == 2 else ""
    if not is_valid_rom_link(rom_link):
        send_message(bot_token, chat_id, USAGE_MESSAGE, reply_to_message_id=message_id)
        return

    try:
        dispatch_workflow(rom_link)
    except Exception:
        send_message(bot_token, chat_id, PUBLIC_FAILURE_MESSAGE, reply_to_message_id=message_id)
        return

    send_message(bot_token, chat_id, PUBLIC_ACK_MESSAGE, reply_to_message_id=message_id)


def main() -> int:
    bot_token = get_env("TELEGRAM_BOT_TOKEN")
    public_chat_id = get_env("TELEGRAM_CHAT_GROUP_ID")
    offset = 0

    while True:
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getUpdates",
            params={
                "timeout": 25,
                "offset": offset,
                "allowed_updates": ["message", "edited_message"],
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()

        for update in payload.get("result", []):
            offset = update["update_id"] + 1
            message = update.get("message") or update.get("edited_message") or {}
            text = (message.get("text") or "").strip()
            if text.startswith("/mezo"):
                handle_mezo_command(bot_token, update, public_chat_id)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    raise SystemExit(main())
