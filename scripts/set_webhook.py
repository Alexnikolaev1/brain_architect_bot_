#!/usr/bin/env python3
"""
🧠 Регистрация Webhook в Telegram

Использование:
  python scripts/set_webhook.py https://your-project.vercel.app/api/webhook
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv(override=True)


async def set_webhook(url: str):
    import httpx

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    api_url = f"https://api.telegram.org/bot{token}/setWebhook"

    async with httpx.AsyncClient() as client:
        r = await client.post(
            api_url,
            json={
                "url": url,
                "allowed_updates": [
                    "message",
                    "callback_query",
                    "pre_checkout_query",
                ],
                "drop_pending_updates": True,
                "max_connections": 40,
            },
        )
        data = r.json()
        if data.get("ok"):
            print(f"✅ Webhook зарегистрирован: {url}")
        else:
            print(f"❌ Ошибка: {data}")


async def get_webhook_info():
    import httpx

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")
        import json
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(set_webhook(sys.argv[1]))
    else:
        asyncio.run(get_webhook_info())
