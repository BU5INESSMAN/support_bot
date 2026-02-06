import logging
from aiogram import Bot
from bot.config import LOG_CHAT_ID, LOG_TOPIC_ID

# Настройка стандартного логгера
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("bot")

async def log_event(bot: Bot, text: str):
    """Отправка лога в спец. топик"""
    try:
        await bot.send_message(
            chat_id=LOG_CHAT_ID,
            text=text,
            message_thread_id=LOG_TOPIC_ID
        )
    except Exception as e:
        logger.error(f"Не удалось отправить лог в Telegram: {e}")