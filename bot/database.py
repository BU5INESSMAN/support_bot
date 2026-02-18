import aiosqlite
import logging

DB_PATH = "support_bot.db"


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
                             status
                             TEXT
                             DEFAULT
                             'open',
                             topic_id
                             INTEGER,
                             first_msg_id
                             INTEGER,
                             created_at
                             TIMESTAMP
                             DEFAULT
                             CURRENT_TIMESTAMP
                         )
                         """)
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS ticket_logs
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             ticket_id
                             INTEGER,
                             sender_role
                             TEXT,
                             text
                             TEXT,
                             timestamp
                             TIMESTAMP
                             DEFAULT
                             CURRENT_TIMESTAMP,
                             FOREIGN
                             KEY
                         (
                             ticket_id
                         ) REFERENCES tickets
                         (
                             id
                         )
                             )
                         """)
        await db.commit()


async def create_ticket(user_id, msg_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO tickets (user_id, first_msg_id) VALUES (?, ?)",
            (user_id, msg_id)
        )
        await db.commit()
        return cursor.lastrowid


async def update_ticket_topic(ticket_id, topic_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET topic_id = ? WHERE id = ?", (topic_id, ticket_id))
        await db.commit()


async def get_active_ticket(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
                "SELECT id FROM tickets WHERE user_id = ? AND status = 'open'",
                (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row['id'] if row else None


async def get_ticket(ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)) as cursor:
            return await cursor.fetchone()


async def get_ticket_by_topic(topic_id):
    """Находит тикет по ID темы в Telegram. Нужно для admin.py"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tickets WHERE topic_id = ?", (topic_id,)) as cursor:
            return await cursor.fetchone()


async def close_ticket_status(ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
        await db.commit()


async def add_log(ticket_id, role, text):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ticket_logs (ticket_id, sender_role, text) VALUES (?, ?, ?)",
            (ticket_id, role, text)
        )
        await db.commit()


async def get_ticket_logs(ticket_id):
    """Возвращает историю переписки по тикету. Нужно для admin.py"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
                "SELECT sender_role, text, timestamp FROM ticket_logs WHERE ticket_id = ? ORDER BY id ASC",
                (ticket_id,)
        ) as cursor:
            return await cursor.fetchall()


async def get_tickets_count(status):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM tickets WHERE status = ?", (status,)) as cursor:
            res = await cursor.fetchone()
            return res[0]


async def get_tickets_paginated(status, page, per_page=10):
    offset = (page - 1) * per_page
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
                "SELECT * FROM tickets WHERE status = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (status, per_page, offset)
        ) as cursor:
            return await cursor.fetchall()


async def cleanup_old_tickets(limit):
    """Удаляет старые ЗАКРЫТЫЕ заявки, если превышен лимит."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("SELECT COUNT(*) FROM tickets") as cursor:
            total_count = (await cursor.fetchone())[0]

        if total_count <= limit:
            return []

        to_delete_count = total_count - limit

        # Берем только закрытые
        async with db.execute(
                "SELECT id, topic_id FROM tickets WHERE status = 'closed' ORDER BY id ASC LIMIT ?",
                (to_delete_count,)
        ) as cursor:
            rows_to_del = await cursor.fetchall()

        if not rows_to_del:
            return []

        ids_to_del = [r['id'] for r in rows_to_del]
        topics_to_del = [r['topic_id'] for r in rows_to_del if r['topic_id']]

        placeholders = ",".join("?" for _ in ids_to_del)
        await db.execute(f"DELETE FROM ticket_logs WHERE ticket_id IN ({placeholders})", ids_to_del)
        await db.execute(f"DELETE FROM tickets WHERE id IN ({placeholders})", ids_to_del)
        await db.commit()

        logging.info(f"♻️ Очистка: удалено {len(ids_to_del)} закрытых заявок.")
        return topics_to_del