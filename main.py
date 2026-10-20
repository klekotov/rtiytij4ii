import asyncio
import logging

from handlers import dp, bot, background_giveaway_checker # Импорт из handlers.py
from utils import start_stats_server, cleanup_old_html_files  # Импорт из utils.py

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    cleanup_old_html_files()
    await start_stats_server()
    asyncio.create_task(background_giveaway_checker())  # Запускаем проверку розыгрышей
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 