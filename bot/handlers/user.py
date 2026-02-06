from aiogram import Router, F, Bot
from aiogram.types import Message
from bot.database import create_ticket, get_active_ticket, save_admin_notification
from bot.config import ADMIN_IDS, SERVICE_NAME
from bot.keyboards import ticket_take_kb, admin_main_menu
import logging

router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("🛠 Панель администратора активирована.", reply_markup=admin_main_menu())
    else:
        await message.answer(f"Привет! Это <b>{SERVICE_NAME}</b>. Опишите вашу проблему:", parse_mode="HTML")


@router.message(F.chat.type == "private")
async def handle_user_message(message: Message, bot: Bot):
    if message.from_user.id in ADMIN_IDS:
        return

    active_ticket = await get_active_ticket(message.from_user.id)

    # Если активного тикета нет — создаем его
    if not active_ticket:
        try:
            ticket_id = await create_ticket(message.from_user.id)
            await message.answer(f"✅ Заявка №{ticket_id} создана. Ожидайте ответа.")

            for admin_id in ADMIN_IDS:
                try:
                    sent = await bot.send_message(
                        admin_id,
                        f"🆕 Новая заявка №{ticket_id} от @{message.from_user.username or message.from_user.id}",
                        reply_markup=ticket_take_kb(ticket_id)
                    )
                    # Важно: записываем в уведомления для удаления кнопок позже
                    await save_admin_notification(ticket_id, admin_id, sent.message_id)
                except Exception as e:
                    logging.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")
            return  # Выходим, так как админ еще не взял тикет
        except Exception as e:
            logging.error(f"Ошибка при создании тикета: {e}")
            await message.answer("Произошла ошибка при создании заявки. Попробуйте позже.")
            return

    # Если тикет есть и его КТО-ТО ВЗЯЛ (есть admin_id)
    if active_ticket and active_ticket['admin_id']:
        try:
            await bot.copy_message(
                chat_id=active_ticket['admin_id'],
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
        except Exception as e:
            logging.error(f"Ошибка пересылки сообщения админу: {e}")
    else:
        # Тикет создан, но админ еще не нажал "Забрать"
        await message.answer("Ваша заявка еще на рассмотрении. Скоро админ подключится.")