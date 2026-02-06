from aiogram import Bot
from aiogram.types import FSInputFile
from bot.config import LOG_CHAT_ID, BACKUP_TOPIC_ID, DB_PATH
from bot.utils.logger import logger

async def send_backup(bot: Bot):
    try:
        file = FSInputFile(DB_PATH)
        await bot.send_document(
            chat_id=LOG_CHAT_ID,
            document=file,
            caption="📦 Ежедневный бэкап базы данных.",
            message_thread_id=BACKUP_TOPIC_ID
        )
    except Exception as e:
        logger.error(f"Backup error: {e}")