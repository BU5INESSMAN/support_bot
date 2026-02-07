import os
from dotenv import load_dotenv

load_dotenv()

# Основные настройки бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
SERVICE_NAME = os.getenv("SERVICE_NAME", "Support Service")

# Настройки чата логов и топиков
LOG_CHAT_ID = int(os.getenv("LOG_CHAT_ID") or 0)
LOG_TOPIC_ID = int(os.getenv("LOG_TOPIC_ID") or 0)
BACKUP_TOPIC_ID = int(os.getenv("BACKUP_TOPIC_ID") or 0)
TIKCET_TOPIC_ID = int(os.getenv("TIKCET_TOPIC_ID") or 0)

# Настройки времени и рабочего графика
TIMEZONE = os.getenv("TZ", "Europe/Moscow")
WORK_START = int(os.getenv("WORK_START", 9)) # По умолчанию 09:00
WORK_END = int(os.getenv("WORK_END", 21))   # По умолчанию 21:00

# Путь к БД. data/ - это папка, которая маунтится в Docker
DB_PATH = "data/database.sqlite"