import asyncio
import logging
import os

# Настраиваем логирование ДО импорта модулей бота, иначе ранний logging.info()
# при импорте выставит root-уровень WARNING и скроет стартовые логи сервера.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True,
)

from handlers import dp, bot, background_giveaway_checker, cookie_processor  # Импорт из handlers.py
from utils import start_stats_server, cleanup_old_html_files  # Импорт из utils.py


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True,
    )
    net_env = {
        k: v for k, v in os.environ.items()
        if any(tag in k.upper() for tag in ("PORT", "HOST", "DOMAIN", "WEB", "APP_URL", "PUBLIC_URL"))
        and not any(sec in k.upper() for sec in ("TOKEN", "SECRET", "PASS", "KEY"))
    }
    logging.info(f"🚀 Запуск бота (build: bothost-fix-v4) | сетевые env: {net_env or 'не заданы'}")
    cleanup_old_html_files()
    await start_stats_server()
    await cookie_processor.resolve_all_games_metadata()
    asyncio.create_task(background_giveaway_checker())  # Запускаем проверку розыгрышей
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
