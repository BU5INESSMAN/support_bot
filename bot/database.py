import aiosqlite
import time
from bot.config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS tickets
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             user_id
                             INTEGER,
                             admin_id
                             INTEGER
                             DEFAULT
                             NULL,
                             status
                             TEXT
                             DEFAULT
                             'open',
                             first_msg_id
                             INTEGER,
                             created_at
                             INTEGER
                         )
                         """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS message_refs (
                admin_chat_id INTEGER,
                admin_message_id INTEGER,
                ticket_id INTEGER,
                PRIMARY KEY (admin_chat_id, admin_message_id)
            )
        """)
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS admin_notifications
                         (
                             ticket_id
                             INTEGER,
                             admin_id
                             INTEGER,
                             message_id
                             INTEGER
                         )
                         """)
        await db.commit()

async def create_ticket(user_id, first_msg_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO tickets (user_id, status, first_msg_id, created_at) VALUES (?, 'open', ?, ?)",
            (user_id, first_msg_id, int(time.time()))
        )
        await db.commit()
        return cursor.lastrowid

async def get_active_ticket(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row # ОБЯЗАТЕЛЬНО
        async with db.execute(
            "SELECT * FROM tickets WHERE user_id = ? AND status = 'open' LIMIT 1",
            (user_id,)
        ) as cursor:
            return await cursor.fetchone()

async def get_tickets_paginated(status='open', page=1, per_page=10):
    offset = (page - 1) * per_page
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Ограничиваем архив 100 записями по ТЗ
        limit_val = 100 if status == 'closed' else 1000
        query = f"SELECT * FROM (SELECT * FROM tickets WHERE status = ? ORDER BY id DESC LIMIT ?) LIMIT ? OFFSET ?"
        async with db.execute(query, (status, limit_val, per_page, offset)) as cursor:
            return await cursor.fetchall()

async def get_tickets_count(status='open'):
    async with aiosqlite.connect(DB_PATH) as db:
        limit_val = 100 if status == 'closed' else 1000
        query = f"SELECT COUNT(*) FROM (SELECT id FROM tickets WHERE status = ? LIMIT ?)"
        async with db.execute(query, (status, limit_val)) as cursor:
            res = await cursor.fetchone()
            return res[0]

async def get_ticket(ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)) as cursor:
            return await cursor.fetchone()

async def update_ticket_admin(ticket_id, admin_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET admin_id = ? WHERE id = ?", (admin_id, ticket_id))
        await db.commit()

async def close_ticket_status(ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
        await db.commit()

async def save_message_ref(admin_chat_id, admin_message_id, ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO message_refs VALUES (?, ?, ?)",
                         (admin_chat_id, admin_message_id, ticket_id))
        await db.commit()

async def get_ticket_by_ref(admin_chat_id, admin_message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT ticket_id FROM message_refs WHERE admin_chat_id = ? AND admin_message_id = ?",
                             (admin_chat_id, admin_message_id)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def save_admin_notification(ticket_id, admin_id, message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO admin_notifications VALUES (?, ?, ?)",
                         (ticket_id, admin_id, message_id))
        await db.commit()

async def get_admin_notifications(ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admin_notifications WHERE ticket_id = ?", (ticket_id,)) as cursor:
            return await cursor.fetchall()

async def get_tickets_count(status='open'):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM tickets WHERE status = ?", (status,)) as cursor:
            res = await cursor.fetchone()
            return res[0] if res else 0

async def get_tickets_paginated(status='open', page=1, per_page=10):
    offset = (page - 1) * per_page
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tickets WHERE status = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (status, per_page, offset)
        ) as cursor:
            return await cursor.fetchall()