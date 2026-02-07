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


# Функция-таймер автозакрытия
async def set_timer_autoclose(ticket_id: int, bot: Bot, delay_hours: int = 3):
    """Ждет 3 часа и закрывает тикет, если он все еще открыт"""
    await asyncio.sleep(delay_hours * 3600)
    ticket = await get_ticket(ticket_id)
    if ticket and ticket['status'] == 'open':
        await close_ticket_status(ticket_id)
        try:
            await bot.send_message(
                ticket['user_id'],
                f"📟 Заявка №{ticket_id} была закрыта автоматически (истекло время ожидания)."
            )
        except:
            pass


@router.callback_query(F.data.startswith("take_"))
async def take_ticket(callback: CallbackQuery, bot: Bot):
    tid = int(callback.data.split("_")[1])
    ticket = await get_ticket(tid)

    if ticket['admin_id']:
        await callback.answer("⚠️ Эту заявку уже забрали!")
        return

    # 1. Назначаем админа
    await update_ticket_admin(tid, callback.from_user.id)

    # 2. Уведомляем пользователя (добавленная функция)
    try:
        await bot.send_message(
            chat_id=int(ticket['user_id']),
            text=f"👨‍💻 <b>Оператор подключился к диалогу.</b>\nЗаявка №{tid}. Вы можете писать сюда.",
            parse_mode="HTML"
        )
    except:
        pass

    # 3. ПЕРЕСЫЛКА ПЕРВОГО СООБЩЕНИЯ (строго по логике коммита)
    try:
        sent = await bot.copy_message(
            chat_id=callback.from_user.id,
            from_chat_id=int(ticket['user_id']),
            message_id=int(ticket['first_msg_id'])
        )
        # Привязываем для Reply
        await save_message_ref(callback.from_user.id, sent.message_id, tid)
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка копирования первого сообщения: {e}")

    # 4. Обновляем уведомления (редактируем сообщение в топике/личке)
    notifications = await get_admin_notifications(tid)
    for auth in notifications:
        try:
            await bot.edit_message_text(
                chat_id=auth['admin_id'],
                message_id=auth['message_id'],
                text=f"✅ Заявку №{tid} взял @{callback.from_user.username or callback.from_user.id}"
            )
            # Также привязываем отредактированное сообщение для ответов
            await save_message_ref(auth['admin_id'], auth['message_id'], tid)
        except:
            pass

    await callback.answer("Заявка принята!")


@router.message(F.reply_to_message)
async def admin_reply(message: Message, bot: Bot):
    """Ответ админа пользователю через Reply"""
    if message.from_user.id not in ADMIN_IDS:
        return

    # Находим ID заявки по сообщению, на которое отвечаем
    tid = await get_ticket_by_ref(message.chat.id, message.reply_to_message.message_id)
    if not tid:
        return  # Если это просто какой-то левый реплай — игнорим

    ticket = await get_ticket(tid)

    # Команда закрытия
    if message.text == "/close":
        await bot.send_message(
            ticket['user_id'],
            f"🛠 Оператор считает проблему по заявке №{tid} решенной. Это так?",
            reply_markup=feedback_kb(tid)
        )
        # Запускаем фоновый таймер на 3 часа
        asyncio.create_task(set_timer_autoclose(tid, bot))
        await message.answer(f"⏳ Запрос подтверждения отправлен. Автозакрытие через 3 часа.")
        return

    # Обычная пересылка ответа пользователю
    try:
        await bot.send_message(
            ticket['user_id'],
            f"<b>Ответ поддержки:</b>\n{message.text}",
            parse_mode="HTML"
        )
        await message.answer("✔️ Отправлено")
        await add_log(tid, "ADMIN", message.text)
    except Exception as e:
        await message.answer(f"❌ Не удалось доставить: {e}")


# --- ПАГИНАЦИЯ И СПИСКИ ---

@router.message(F.text.in_(["Открытые заявки", "Архив заявок"]))
async def list_tickets(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    status = 'open' if message.text == "Открытые заявки" else 'closed'
    count = await get_tickets_count(status)
    tickets = await get_tickets_paginated(status, page=1)

    if not tickets:
        await message.answer(f"Список {message.text.lower()} пуст.")
        return

    await message.answer(
        f"📂 {message.text}:",
        reply_markup=tickets_list_kb(tickets, 1, count, status)
    )


@router.callback_query(F.data.startswith("list_"))
async def list_nav(callback: CallbackQuery):
    """Навигация по страницам (Вперед/Назад)"""
    _, status, page = callback.data.split("_")
    page = int(page)

    count = await get_tickets_count(status)
    tickets = await get_tickets_paginated(status, page)

    await callback.message.edit_reply_markup(
        reply_markup=tickets_list_kb(tickets, page, count, status)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("view_"))
async def view_ticket(callback: CallbackQuery, bot: Bot):
    tid = int(callback.data.split("_")[1])
    ticket = await get_ticket(tid)

    if not ticket:
        await callback.answer("Заявка не найдена.")
        return

    # Определяем статус текстом
    status_text = "✅ Открыта" if ticket['status'] == 'open' else "📁 В архиве"

    # Формируем дату создания
    created_date = datetime.fromtimestamp(ticket['created_at']).strftime('%d.%m.%Y %H:%M')

    text = (
        f"🎫 <b>Заявка №{tid}</b>\n\n"
        f"📊 <b>Статус:</b> {status_text}\n"
        f"👤 <b>Юзер:</b> <code>{ticket['user_id']}</code>\n"
        f"📅 <b>Создана:</b> {created_date}\n"
        f"👨‍💻 <b>Админ:</b> {ticket['admin_id'] if ticket['admin_id'] else 'Не назначен'}"
    )

    # Отправляем карточку заявки с кнопкой просмотра истории
    await callback.message.answer(text, reply_markup=ticket_view_kb(tid), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("view_"))
async def view_ticket_history(callback: CallbackQuery):
    tid = int(callback.data.split("_")[1])
    ticket = await get_ticket(tid)
    logs = await get_ticket_logs(tid)

    status_emoji = "🟢" if ticket['status'] == 'open' else "🔴"
    header = f"{status_emoji} <b>История заявки №{tid}</b>\n"
    header += f"👤 Юзер ID: <code>{ticket['user_id']}</code>\n"
    header += f"📅 Создана: {datetime.fromtimestamp(ticket['created_at']).strftime('%d.%m %H:%M')}\n"
    header += "--------------------------\n"

    if not logs:
        history_text = "Логи переписки пусты или не велись."
    else:
        history_text = ""
        for log in logs:
            role_label = "👤 Юзер" if log['sender_role'] == "USER" else "👨‍💻 Админ"
            history_text += f"<b>{role_label}:</b> {log['text']}\n"

    # Если текст слишком длинный, Телеграм его не пропустит (лимит 4096 символов)
    full_text = header + history_text
    if len(full_text) > 4000:
        full_text = full_text[:3900] + "\n... (слишком длинная история)"

    await callback.message.answer(full_text, parse_mode="HTML")
    await callback.answer()