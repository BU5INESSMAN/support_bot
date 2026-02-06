from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from bot.database import (
    get_tickets_paginated, get_tickets_count, get_ticket,
    update_ticket_admin, close_ticket_status, get_ticket_by_ref, save_message_ref,get_admin_notifications
)
from bot.keyboards import tickets_list_kb, ticket_take_kb, feedback_kb
from bot.config import ADMIN_IDS

router = Router()


@router.callback_query(F.data.startswith("take_"))
async def take_ticket(callback: CallbackQuery, bot: Bot):
    tid = int(callback.data.split("_")[1])
    ticket = await get_ticket(tid)

    if ticket['admin_id']:
        await callback.answer("⚠️ Эту заявку уже забрали!", show_alert=True)
        return

    await update_ticket_admin(tid, callback.from_user.id)

    # ЛОГИКА УДАЛЕНИЯ КНОПОК У ВСЕХ
    notifications = await get_admin_notifications(tid)
    for auth in notifications:
        try:
            await bot.edit_message_text(
                chat_id=auth['admin_id'],
                message_id=auth['message_id'],
                text=f"✅ <b>Заявку №{tid} взял @{callback.from_user.username}</b>",
                parse_mode="HTML"
            )
        except:
            pass  # Если админ удалил сообщение с кнопкой

    # Уведомляем пользователя и устанавливаем контакт
    await bot.send_message(ticket['user_id'], f"👨‍💻 Админ подключился к заявке №{tid}. Ждем ваш вопрос.")
    await callback.answer()


# Хендлер ответа (Админ -> Юзер)
@router.message(F.reply_to_message)
async def admin_reply(message: Message, bot: Bot):
    if message.from_user.id not in ADMIN_IDS:
        return

    # Пытаемся найти ID тикета по сообщению, на которое ответил админ
    tid = await get_ticket_by_ref(message.chat.id, message.reply_to_message.message_id)

    if tid:
        ticket = await get_ticket(tid)
        if message.text == "/close":
            await close_ticket_status(tid)
            await bot.send_message(ticket['user_id'], "✅ Ваша проблема решена? (Да/Нет)", reply_markup=feedback_kb(tid))
            await message.answer(f"🏁 Заявка №{tid} закрыта.")
        else:
            # Пересылаем ответ пользователю
            await bot.copy_message(ticket['user_id'], message.chat.id, message.message_id)
            # Опционально: ставим реакцию, что сообщение ушло
            await message.react([{"type": "emoji", "emoji": "📨"}])
    else:
        # Если админ ответил на сообщение, которого нет в базе связок
        await message.answer(
            "⚠️ Не удалось найти заявку для этого сообщения. Отвечайте именно на сообщение пользователя.")