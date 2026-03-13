"""
🧠 АРХИТЕКТОР МОЗГА — Vercel Serverless Entry Point
POST /api/webhook — принимает апдейты от Telegram
"""

import asyncio
import json
import logging
from http.server import BaseHTTPRequestHandler

from telegram import Update
from telegram.ext import Application

from app.bot import create_application

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class handler(BaseHTTPRequestHandler):
    """Vercel Serverless Function handler."""

    def do_POST(self):  # noqa: N802
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            if not body:
                self.send_response(400)
                self.end_headers()
                return
            asyncio.run(self._process_update(body))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": false, "error": "invalid_json"}')
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error processing update: %s", exc)
            self.send_response(500)
            self.end_headers()

    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "Brain Architect Bot is alive \xf0\x9f\xa7\xa0"}')

    async def _process_update(self, body: bytes) -> None:
        app = await create_application()
        data = json.loads(body)
        update = Update.de_json(data, app.bot)
        async with app:
            await app.process_update(update)

    def log_message(self, *args):  # suppress default logging
        pass
