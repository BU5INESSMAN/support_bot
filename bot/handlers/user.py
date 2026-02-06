import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.utils.media_group import MediaGroupBuilder
from bot.database import (
    create_ticket,
    get_active_ticket,
    save_admin_notification,
    save_message_ref
)
from bot.config import ADMIN_IDS, SERVICE_NAME
from bot.keyboards import ticket_take_kb, admin_main_menu

router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    """Приветствие и инициализация меню для админов"""
    if message.from_user.id in ADMIN_IDS:
        await message.answer(
            "🛠 Панель администратора активирована.\nИспользуйте кнопки меню для управления заявками.",
            reply_markup=admin_main_menu()
        )
    else:
        await message.answer(
            f"Привет! Это техподдержка **{SERVICE_NAME}**\n"
            "Опишите вашу проблему в одном сообщении, и мы создадим заявку.\n"
            "Бот поддерживает отправку медиа (Фото, Видео, Звук, PDF)\n",
            parse_mode="HTML"
        )


@router.message(F.chat.type == "private")
async def handle_user_message(message: Message, bot: Bot, album: list[Message] = None):
    """Обработка всех входящих сообщений от пользователей"""

    # Игнорируем сообщения от админов (чтобы они не создавали тикеты сами себе)
    if message.from_user.id in ADMIN_IDS:
        return

        # Ищем активную открытую заявку
    active_ticket = await get_active_ticket(message.from_user.id)

    if not active_ticket:
        try:
            # 1. Создаем тикет в БД
            ticket_id = await create_ticket(message.from_user.id, message.message_id)
            await message.answer(f"✅ Заявка №{ticket_id} создана. Ожидайте ответа оператора.")

            # 2. Формируем текст для админов (берем текст или описание медиа)
            user_text = message.text or message.caption or "[Медиа-файл]"
            # Обрезаем слишком длинные сообщения, чтобы не ломать верстку телеграма
            preview_text = (user_text[:200] + '...') if len(user_text) > 200 else user_text

            admin_alert_text = (
                f"🆕 <b>Новая заявка №{ticket_id}</b>\n"
                f"👤 От: @{message.from_user.username or message.from_user.id}\n"
                f"📝 <b>Текст:</b> <i>{preview_text}</i>"
            )

            # 3. Рассылаем уведомление
            for admin_id in ADMIN_IDS:
                try:
                    sent = await bot.send_message(
                        admin_id,
                        admin_alert_text,
                        reply_markup=ticket_take_kb(ticket_id),
                        parse_mode="HTML"
                    )
                    await save_admin_notification(ticket_id, admin_id, sent.message_id)
                except Exception as e:
                    logging.error(f"Ошибка уведомления админа: {e}")
            return
        except Exception as e:
            logging.error(f"Ошибка при создании тикета: {e}")
            await message.answer("Произошла ошибка. Попробуйте написать позже.")
            return

    # 2. Если заявка есть, но админ ещё не нажал "Забрать"
    if not active_ticket['admin_id']:
        await message.answer("⏳ Ваша заявка №{} уже в очереди. Скоро оператор ответит вам.".format(active_ticket['id']))
        return

    # 3. Если заявка принята админом — пересылаем сообщение ему
    admin_chat_id = active_ticket['admin_id']
    ticket_id = active_ticket['id']

    try:
        if album:
            # Обработка альбомов (фото/видео)
            mg = MediaGroupBuilder(caption=f"📨 Сообщение по тикету #{ticket_id}")
            for m in album:
                if m.photo:
                    mg.add_photo(m.photo[-1].file_id)
                elif m.video:
                    mg.add_video(m.video.file_id)
                elif m.document:
                    mg.add_document(m.document.file_id)

            sent_msgs = await bot.send_media_group(admin_chat_id, media=mg.build())
            # Привязываем первое сообщение из группы к тикету для Reply
            await save_message_ref(admin_chat_id, sent_msgs[0].message_id, ticket_id)

        else:
            # Обычное текстовое или одиночное медиа сообщение
            sent = await bot.copy_message(
                chat_id=admin_chat_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            # КРИТИЧЕСКИ ВАЖНО: сохраняем связь для возможности ответа
            await save_message_ref(admin_chat_id, sent.message_id, ticket_id)

    except Exception as e:
        logging.error(f"Ошибка пересылки сообщения админу {admin_chat_id}: {e}")
        await message.answer("⚠️ Не удалось доставить сообщение оператору. Попробуйте еще раз.")