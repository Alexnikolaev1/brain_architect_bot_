#!/usr/bin/env python3
"""
🧠 Локальный запуск бота (polling mode для разработки)

Использование:
  python run_local.py

Требует .env файл с переменными окружения.
"""

import asyncio
import logging

from dotenv import load_dotenv

# Always prefer project .env over system/user environment variables.
load_dotenv(override=True)

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    level=logging.INFO,
)
# Avoid leaking bot token in verbose HTTP request logs.
logging.getLogger("httpx").setLevel(logging.WARNING)

from app.bot import create_application


def main():
    app = asyncio.run(create_application())
    print("🧠 Архитектор Мозга запускается (polling)...")
    print("   Нажми Ctrl+C для остановки")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
