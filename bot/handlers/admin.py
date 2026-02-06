from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
import aiosqlite
from bot.database import (
    get_tickets_paginated, get_tickets_count, get_ticket,
    update_ticket_admin, close_ticket_status, get_ticket_by_ref, save_message_ref
)
from bot.keyboards import tickets_list_kb, ticket_take_kb, feedback_kb
from bot.config import ADMIN_IDS, DB_PATH

router = Router()


@router.message(F.text.in_(["Открытые заявки", "Архив заявок"]))
async def show_list(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    status = 'open' if message.text == "Открытые заявки" else 'closed'
    count = await get_tickets_count(status)
    tickets = await get_tickets_paginated(status, 1)
    await message.answer(f"📂 {message.text}:", reply_markup=tickets_list_kb(tickets, 1, count, status))


@router.callback_query(F.data.startswith("list_"))
async def list_nav(callback: CallbackQuery):
    _, status, page = callback.data.split("_")
    page = int(page)
    count = await get_tickets_count(status)
    tickets = await get_tickets_paginated(status, page)
    await callback.message.edit_reply_markup(reply_markup=tickets_list_kb(tickets, page, count, status))


@router.callback_query(F.data.startswith("view_"))
async def view_ticket_detail(callback: CallbackQuery):
    ticket_id = int(callback.data.split("_")[1])
    ticket = await get_ticket(ticket_id)
    text = f"🎫 <b>Заявка №{ticket_id}</b>\nСтатус: {ticket['status']}\nЮзер: {ticket['user_id']}"
    kb = ticket_take_kb(ticket_id) if ticket['status'] == 'open' and not ticket['admin_id'] else None
    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("take_"))
async def take_ticket(callback: CallbackQuery, bot: Bot):
    tid = int(callback.data.split("_")[1])
    await update_ticket_admin(tid, callback.from_user.id)
    await callback.message.edit_text(f"✅ Вы взяли заявку №{tid}")
    ticket = await get_ticket(tid)
    await bot.send_message(ticket['user_id'], f"👨‍💻 Админ подключился к заявке №{tid}")


@router.message(F.reply_to_message)
async def admin_reply(message: Message, bot: Bot):
    if message.from_user.id not in ADMIN_IDS: return
    tid = await get_ticket_by_ref(message.chat.id, message.reply_to_message.message_id)
    if not tid: return

    ticket = await get_ticket(tid)
    if message.text == "/close":
        await close_ticket_status(tid)
        await message.answer(f"🏁 Тикет №{tid} закрыт.")
        await bot.send_message(ticket['user_id'], "Заявка закрыта. Помогло?", reply_markup=feedback_kb(tid))
    else:
        # При ответе админа также сохраняем референс, чтобы юзер мог ответить на это сообщение
        sent = await bot.copy_message(ticket['user_id'], message.chat.id, message.message_id)