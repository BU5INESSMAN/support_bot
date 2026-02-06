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
        await callback.answer("⚠️ Эту заявку уже забрали!")
        return

    await update_ticket_admin(tid, callback.from_user.id)

    # Можно извлечь старый текст из сообщения, чтобы не потерять его при редактировании
    old_text = callback.message.text.split("📝 Текст:")[0] if "📝 Текст:" in callback.message.text else f"Заявка №{tid}"

    notifications = await get_admin_notifications(tid)
    for auth in notifications:
        try:
            await bot.edit_message_text(
                chat_id=auth['admin_id'],
                message_id=auth['message_id'],
                text=f"{old_text}\n\n✅ <b>Взял: @{callback.from_user.username}</b>",
                parse_mode="HTML"
            )
            await save_message_ref(auth['admin_id'], auth['message_id'], tid)
        except:
            pass

    # 2. АВТО-ПЕРЕСЫЛКА ПЕРВОГО СООБЩЕНИЯ
    try:
        sent = await bot.copy_message(
            chat_id=callback.from_user.id,
            from_chat_id=ticket['user_id'],
            message_id=ticket['first_msg_id']
        )
        # Регистрируем это скопированное сообщение в базе ответов
        await save_message_ref(callback.from_user.id, sent.message_id, tid)

        await callback.message.answer("👆 Выше первое сообщение пользователя. Ответьте на него через Reply.")
    except Exception as e:
        await callback.message.answer(
            "⚠️ Не удалось переслать текст первого сообщения, но вы можете ждать новых сообщений от юзера.")

    await bot.send_message(ticket['user_id'], f"👨‍💻 Оператор на связи.")
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

