import aiosqlite
import time
from bot.config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица тикетов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                admin_id INTEGER DEFAULT NULL,
                status TEXT DEFAULT 'open', 
                created_at INTEGER
            )
        """)
        # Таблица связок: Сообщение в чате админа <-> Тикет
        # Это нужно, чтобы понимать, к какому тикету относится Reply админа
        await db.execute("""
            CREATE TABLE IF NOT EXISTS message_refs (
                admin_chat_id INTEGER,
                admin_message_id INTEGER,
                ticket_id INTEGER,
                PRIMARY KEY (admin_chat_id, admin_message_id)
            )
        """)
        await db.commit()

# --- Работа с тикетами ---
async def create_ticket(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO tickets (user_id, status, created_at) VALUES (?, 'open', ?)",
            (user_id, int(time.time()))
        )
        await db.commit()
        return cursor.lastrowid

async def get_active_ticket(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tickets WHERE user_id = ? AND status = 'open' LIMIT 1",
            (user_id,)
        ) as cursor:
            return await cursor.fetchone()

async def get_ticket(ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)) as cursor:
            return await cursor.fetchone()

async def count_active_tickets(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM tickets WHERE user_id = ? AND status = 'open'",
            (user_id,)
        ) as cursor:
            return (await cursor.fetchone())[0]

async def update_ticket_admin(ticket_id, admin_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET admin_id = ? WHERE id = ?", (admin_id, ticket_id))
        await db.commit()

async def close_ticket_status(ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
        await db.commit()

async def reopen_ticket_status(ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET status = 'open' WHERE id = ?", (ticket_id,))
        await db.commit()

# --- Работа с референсами сообщений ---
async def save_message_ref(admin_chat_id, admin_message_id, ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO message_refs (admin_chat_id, admin_message_id, ticket_id) VALUES (?, ?, ?)",
            (admin_chat_id, admin_message_id, ticket_id)
        )
        await db.commit()

async def get_ticket_by_ref(admin_chat_id, admin_message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT ticket_id FROM message_refs WHERE admin_chat_id = ? AND admin_message_id = ?",
            (admin_chat_id, admin_message_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

