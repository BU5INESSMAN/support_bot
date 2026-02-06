import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
LOG_CHAT_ID = int(os.getenv("LOG_CHAT_ID"))
LOG_TOPIC_ID = int(os.getenv("LOG_TOPIC_ID") or 0)
BACKUP_TOPIC_ID = int(os.getenv("BACKUP_TOPIC_ID") or 0)
SERVICE_NAME = os.getenv("SERVICE_NAME", "Support Service")
TIMEZONE = "Europe/Moscow"

# Путь к БД. data/ - это папка, которая будет маунтиться в Docker
DB_PATH = "data/database.sqlite"