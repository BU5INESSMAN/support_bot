import asyncio
import pytz
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from bot.database import (
    get_tickets_paginated, get_tickets_count, get_ticket,
    update_ticket_admin, close_ticket_status, get_ticket_by_ref,
    save_message_ref, get_admin_notifications, get_ticket_logs, add_log
)
from bot.keyboards import tickets_list_kb, feedback_kb, ticket_view_kb
from bot.config import ADMIN_IDS

router = Router()

async def set_timer_autoclose(ticket_id: int, bot: Bot, delay_hours: int = 3):
    await asyncio.sleep(delay_hours * 3600)
    ticket = await get_ticket(ticket_id)
    if ticket and ticket['status'] == 'open':
        await close_ticket_status(ticket_id)
        try:
            await bot.send_message(ticket['user_id'], f"📟 Заявка №{ticket_id} закрыта автоматически.")
        except: pass

@router.callback_query(F.data.startswith("take_"))
async def take_ticket(callback: CallbackQuery, bot: Bot):
    tid = int(callback.data.split("_")[1])
    ticket = await get_ticket(tid)

    if ticket['admin_id']:
        await callback.answer("⚠️ Эту заявку уже забрали!")
        return

    await update_ticket_admin(tid, callback.from_user.id)

    try:
        await bot.send_message(
            chat_id=int(ticket['user_id']),
            text=f"👨‍💻 <b>Оператор подключился к диалогу.</b>\nЗаявка №{tid}.",
            parse_mode="HTML"
        )
    except: pass

    # КОПИРУЕМ ПЕРВОЕ СООБЩЕНИЕ АДМИНУ
    try:
        sent = await bot.copy_message(
            chat_id=callback.from_user.id,
            from_chat_id=int(ticket['user_id']),
            message_id=int(ticket['first_msg_id'])
        )
        await save_message_ref(callback.from_user.id, sent.message_id, tid)
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка копирования первого сообщения: {e}")

    notifications = await get_admin_notifications(tid)
    for auth in notifications:
        try:
            await bot.edit_message_text(
                chat_id=auth['admin_id'],
                message_id=auth['message_id'],
                text=f"✅ Заявку №{tid} взял @{callback.from_user.username or callback.from_user.id}"
            )
            await save_message_ref(auth['admin_id'], auth['message_id'], tid)
        except: pass

    await callback.answer("Заявка принята!")

@router.message(F.reply_to_message)
async def admin_reply(message: Message, bot: Bot):
    if message.from_user.id not in ADMIN_IDS: return

    tid = await get_ticket_by_ref(message.chat.id, message.reply_to_message.message_id)
    if not tid: return

    ticket = await get_ticket(tid)

    if message.text == "/close":
        await bot.send_message(ticket['user_id'], f"🛠 Вопрос по заявке №{tid} решен?", reply_markup=feedback_kb(tid))
        asyncio.create_task(set_timer_autoclose(tid, bot))
        await message.answer("⏳ Запрос отправлен.")
        return

    # ИСПРАВЛЕНИЕ: Используем copy_message вместо send_message
    try:
        await bot.copy_message(
            chat_id=ticket['user_id'],
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        await add_log(tid, "ADMIN", message.text or message.caption or "[Медиа]")
        await message.answer("✔️ Отправлено")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(F.text.in_(["Открытые заявки", "Архив заявок"]))
async def list_tickets(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    status = 'open' if message.text == "Открытые заявки" else 'closed'
    count = await get_tickets_count(status)
    tickets = await get_tickets_paginated(status, 1)
    if not tickets:
        await message.answer(f"Список {message.text.lower()} пуст.")
        return
    await message.answer(f"📂 {message.text}:", reply_markup=tickets_list_kb(tickets, 1, count, status))

@router.callback_query(F.data.startswith("list_"))
async def list_nav(callback: CallbackQuery):
    _, status, page = callback.data.split("_")
    page = int(page)
    count = await get_tickets_count(status)
    tickets = await get_tickets_paginated(status, page)
    await callback.message.edit_reply_markup(reply_markup=tickets_list_kb(tickets, page, count, status))
    await callback.answer()

@router.callback_query(F.data.startswith("view_"))
async def view_ticket_info(callback: CallbackQuery):
    tid = int(callback.data.split("_")[1])
    ticket = await get_ticket(tid)
    if not ticket:
        await callback.answer("Не найдено.")
        return
    status_text = "✅ Открыта" if ticket['status'] == 'open' else "📁 В архиве"
    text = f"🎫 <b>Заявка №{tid}</b>\n\n📊 Статус: {status_text}\n👤 Юзер: {ticket['user_id']}"
    await callback.message.answer(text, reply_markup=ticket_view_kb(tid), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("history_"))
async def show_history(callback: CallbackQuery):
    tid = int(callback.data.split("_")[1])
    logs = await get_ticket_logs(tid)
    if not logs:
        await callback.answer("История пуста.", show_alert=True)
        return
    history_text = f"📖 <b>История №{tid}:</b>\n\n"
    for log in logs:
        role = "👤 Юзер" if log['sender_role'] == "USER" else "👨‍💻 Админ"
        history_text += f"<b>{role}:</b> {log['text']}\n"
    await callback.message.answer(history_text[:4000], parse_mode="HTML")
    await callback.answer()
