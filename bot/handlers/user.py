import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from bot.database import (
    create_ticket,
    get_active_ticket,
    save_admin_notification,
    save_message_ref,
    get_ticket,
    close_ticket_status, add_log
)
from bot.config import (
    ADMIN_IDS, SERVICE_NAME, LOG_CHAT_ID,
    TIKCET_TOPIC_ID, WORK_START, WORK_END, TIMEZONE
)
from bot.keyboards import ticket_take_kb, admin_main_menu, feedback_kb
from datetime import datetime
import pytz

router = Router()


def is_working_hours():
    """Проверка, входит ли текущее время в рабочий диапазон"""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    return WORK_START <= now.hour < WORK_END


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    """Приветствие: админам — меню, юзерам — приглашение писать"""
    if message.from_user.id in ADMIN_IDS:
        await message.answer(
            "🛠 Панель администратора активирована.\nИспользуйте кнопки меню для управления заявками.",
            reply_markup=admin_main_menu()
        )
    else:
        await message.answer(
            f"Привет! Это техподдержка <b>{SERVICE_NAME}</b>\n"
            "Опишите вашу проблему в одном сообщении, и мы вам поможем!",
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("solved_"))
async def handle_feedback(callback: CallbackQuery, bot: Bot):
    """Обработка кнопок 'Да/Нет' от пользователя при закрытии"""
    _, answer, tid = callback.data.split("_")
    tid = int(tid)
    ticket = await get_ticket(tid)

    if answer == "yes":
        await close_ticket_status(tid)
        await callback.message.edit_text("✅ Мы рады, что проблема решена! Заявка закрыта.")
        if ticket and ticket['admin_id']:
            await bot.send_message(ticket['admin_id'], f"✅ Пользователь подтвердил решение по заявке №{tid}.")
    else:
        await callback.message.edit_text("⚠️ Заявка остается открытой. Оператор свяжется с вами для уточнения деталей.")
        if ticket and ticket['admin_id']:
            await bot.send_message(ticket['admin_id'],
                                   f"❌ Пользователь сообщил, что проблема по заявке №{tid} НЕ решена.")

    await callback.answer()


@router.message(F.chat.type == "private")
async def handle_user_msg(message: Message, bot: Bot):
    if message.from_user.id in ADMIN_IDS: return

    active_tid = await get_active_ticket(message.from_user.id)

    # СОЗДАНИЕ НОВОЙ ЗАЯВКИ
    if not active_tid:
        # Проверка часов (наша функция)
        if not is_working_hours():
            await message.answer(f"🌙 Сейчас нерабочее время ({WORK_START}:00-{WORK_END}:00 МСК). Мы ответим позже.")
            # Но заявку все равно создаем!

        tid = await create_ticket(message.from_user.id, message.message_id)

        # Текст для топика
        user_text = message.text or message.caption or "[Медиа]"
        alert = f"🆕 <b>Новая заявка №{tid}</b>\n👤 От: @{message.from_user.username}\n📝 Текст: {user_text[:200]}"

        # Отправка в топик (наша функция)
        try:
            grp = await bot.send_message(LOG_CHAT_ID, alert, message_thread_id=TIKCET_TOPIC_ID,
                                         reply_markup=ticket_take_kb(tid), parse_mode="HTML")
            await save_admin_notification(tid, LOG_CHAT_ID, grp.message_id)
        except:
            pass

        # В личку админам
        for aid in ADMIN_IDS:
            try:
                sent = await bot.send_message(aid, alert, reply_markup=ticket_take_kb(tid), parse_mode="HTML")
                await save_admin_notification(tid, aid, sent.message_id)
            except:
                pass

        await message.answer(f"✅ Заявка №{tid} создана. Ожидайте оператора.")
        return

    # ПЕРЕСЫЛКА ПОСЛЕДУЮЩИХ СООБЩЕНИЙ (если заявка уже есть)
    ticket = await get_ticket(active_tid)
    if ticket and ticket['admin_id']:
        try:
            sent = await bot.copy_message(
                chat_id=int(ticket['admin_id']),
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            # Когда юзер пишет:
            await add_log(active_tid, "USER", message.text or "[Медиа]")
            await save_message_ref(int(ticket['admin_id']), sent.message_id, active_tid)
        except Exception as e:
            logging.error(f"Error forwarding: {e}")
    else:
        # Если заявка есть, но кнопку еще не нажали
        await message.answer("⏳ Оператор еще не подключился к вашей заявке №{}. Ожидайте.".format(active_tid))