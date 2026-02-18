from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from bot.database import (
    get_tickets_paginated, get_tickets_count, get_ticket,
    close_ticket_status, get_ticket_logs, add_log, get_ticket_by_topic
)
from bot.keyboards import tickets_list_kb, feedback_kb, ticket_view_kb
from bot.config import ADMIN_IDS, LOG_CHAT_ID

router = Router()

# Кружки для админки
CIRCLE_RED = "\U0001F534"
CIRCLE_GREEN = "\U0001F7E2"


@router.message(F.chat.id == LOG_CHAT_ID)
async def handle_admin_reply(message: Message, bot: Bot):
    if not message.message_thread_id or message.from_user.is_bot:
        return

    ticket = await get_ticket_by_topic(message.message_thread_id)
    if not ticket: return

    if message.text == "/close":
        await bot.send_message(
            ticket['user_id'],
            f"🛠 *Вопрос по заявке №{ticket['id']} решен?*",
            reply_markup=feedback_kb(ticket['id']),
            parse_mode="Markdown"
        )
        await message.answer("⏳ *Запрос отправлен пользователю.*", parse_mode="Markdown")
        return

    try:
        await bot.copy_message(
            chat_id=ticket['user_id'],
            from_chat_id=LOG_CHAT_ID,
            message_id=message.message_id
        )
        await add_log(ticket['id'], "ADMIN", message.text or message.caption or "[Медиа]")
    except Exception as e:
        await message.answer(f"❌ *Ошибка отправки:* `{e}`", parse_mode="Markdown")


@router.message(F.text.in_(["Открытые заявки", "Архив заявок"]))
async def list_tickets(message: Message):
    if message.from_user.id not in ADMIN_IDS: return

    is_open = message.text == "Открытые заявки"
    status = 'open' if is_open else 'closed'
    icon = CIRCLE_RED if is_open else CIRCLE_GREEN

    count = await get_tickets_count(status)
    tickets = await get_tickets_paginated(status, 1)

    await message.answer(
        f"{icon} *{message.text}:*",
        reply_markup=tickets_list_kb(tickets, 1, count, status),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("view_"))
async def view_ticket_info(callback: CallbackQuery):
    tid = int(callback.data.split("_")[1])
    ticket = await get_ticket(tid)
    icon = CIRCLE_RED if ticket['status'] == 'open' else CIRCLE_GREEN

    text = f"🎫 *Заявка №{tid}*\n\n📊 Статус: {icon} `{ticket['status']}`\n👤 Юзер: `{ticket['user_id']}`"
    await callback.message.answer(text, reply_markup=ticket_view_kb(tid), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("history_"))
async def show_history(callback: CallbackQuery):
    tid = int(callback.data.split("_")[1])
    logs = await get_ticket_logs(tid)
    history_text = f"📖 *История №{tid}:*\n\n"
    for log in logs:
        role = "👤 *Юзер*" if log['sender_role'] == "USER" else "👨‍💻 *Админ*"
        history_text += f"{role}: {log['text']}\n"
    await callback.message.answer(history_text[:4000], parse_mode="Markdown")
    await callback.answer()