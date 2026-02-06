import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import BOT_TOKEN, TIMEZONE
from bot.database import init_db
from bot.handlers import user, admin
from bot.middlewares.album import AlbumMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.utils.backup import send_backup
from bot.utils.logger import log_event


async def main():
    # Инициализация БД
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware (порядок важен)
    dp.message.middleware(ThrottlingMiddleware())  # Сначала защита от спама
    dp.message.middleware(AlbumMiddleware())  # Потом сборка альбомов

    # Роутеры
    dp.include_router(admin.router)
    dp.include_router(user.router)

    # Планировщик (бэкапы раз в сутки в 00:00)
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_backup, 'cron', hour=0, minute=0, kwargs={'bot': bot})
    scheduler.start()

    await log_event(bot, "🚀 **Бот техподдержки запущен!**")

    try:
        await dp.start_polling(bot)
    finally:
        await log_event(bot, "🛑 **Бот остановлен**")
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass