import logging
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from bot.database import (
    create_ticket, get_active_ticket, get_ticket,
    close_ticket_status, add_log, update_ticket_topic,
    cleanup_old_tickets
)
from bot.config import (
    ADMIN_IDS, SERVICE_NAME, LOG_CHAT_ID,
    WORK_START, WORK_END, TIMEZONE, TICKETS_LIMIT
)
from bot.keyboards import admin_main_menu
from datetime import datetime
import pytz

router = Router()

CIRCLE_RED = "🔴"
CIRCLE_GREEN = "🟢"


def is_working_hours():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    return WORK_START <= now.hour < WORK_END


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("*🛠 Админ-панель*", reply_markup=admin_main_menu(), parse_mode="Markdown")
    else:
        await message.answer(f"Привет! Это техподдержка *{SERVICE_NAME}*. Опишите вашу проблему!",
                             parse_mode="Markdown")


@router.callback_query(F.data.startswith("solved_"))
async def handle_feedback(callback: CallbackQuery, bot: Bot):
    _, answer, tid = callback.data.split("_")
    ticket = await get_ticket(int(tid))
    if not ticket: return

    user_info = f"@{callback.from_user.username}" if callback.from_user.username else f"ID {ticket['user_id']}"

    if answer == "yes":
        await close_ticket_status(int(tid))
        await callback.message.edit_text("✅ *Заявка закрыта.*", parse_mode="Markdown")
        if ticket['topic_id']:
            try:
                new_name = f"{CIRCLE_GREEN} РЕШЕНО | №{tid} | {user_info}"
                await bot.edit_forum_topic(LOG_CHAT_ID, ticket['topic_id'], name=new_name)
                await asyncio.sleep(1)
                await bot.close_forum_topic(LOG_CHAT_ID, ticket['topic_id'])
            except Exception as e:
                logging.error(f"Error closing topic: {e}")
    else:
        await callback.message.edit_text("⚠️ *Оператор свяжется с вами.*", parse_mode="Markdown")
        if ticket['topic_id']:
            try:
                await bot.send_message(
                    LOG_CHAT_ID,
                    f"❌ *Внимание!* Юзер сообщил, что проблема по заявке №{tid} *НЕ решена*.",
                    message_thread_id=ticket['topic_id'],
                    parse_mode="Markdown"
                )
            except:
                pass
    await callback.answer()


@router.message(F.chat.type == "private")
async def handle_user_msg(message: Message, bot: Bot):
    if message.from_user.id in ADMIN_IDS: return

    active_tid = await get_active_ticket(message.from_user.id)

    if not active_tid:
        if not is_working_hours():
            await message.answer(
                f"🌙 Все специалисты сейчас заняты. Мы ответим вам с *{WORK_START}:00* до *{WORK_END}:00* (МСК).",
                parse_mode="Markdown"
            )

        tid = await create_ticket(message.from_user.id, message.message_id)
        await add_log(tid, "USER", message.text or message.caption or "[Медиа]")

        try:
            user_name = f"@{message.from_user.username}" if message.from_user.username else f"ID {message.from_user.id}"
            topic = await bot.create_forum_topic(
                LOG_CHAT_ID,
                name=f"{CIRCLE_RED} Заявка №{tid} | {user_name}"
            )
            await update_ticket_topic(tid, topic.message_thread_id)
            await bot.copy_message(LOG_CHAT_ID, message.chat.id, message.message_id,
                                   message_thread_id=topic.message_thread_id)

            # Очистка старых закрытых заявок
            topics_to_del = await cleanup_old_tickets(TICKETS_LIMIT)
            for t_id in topics_to_del:
                try:
                    await bot.delete_forum_topic(LOG_CHAT_ID, t_id)
                    await asyncio.sleep(0.3)
                except:
                    pass

        except Exception as e:
            logging.error(f"Creation error: {e}")

        await message.answer(f"✅ *Заявка №{tid} создана. Ожидайте ответа оператора.*", parse_mode="Markdown")
        return

    ticket = await get_ticket(active_tid)
    if ticket and ticket['topic_id']:
        try:
            await bot.copy_message(LOG_CHAT_ID, message.chat.id, message.message_id,
                                   message_thread_id=ticket['topic_id'])
            await add_log(active_tid, "USER", message.text or message.caption or "[Медиа]")
        except:
            pass