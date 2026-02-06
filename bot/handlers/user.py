from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.media_group import MediaGroupBuilder

from bot.database import (
    create_ticket, get_active_ticket, count_active_tickets,
    save_message_ref, reopen_ticket_status, close_ticket_status
)
from bot.config import ADMIN_IDS, SERVICE_NAME
from bot.keyboards import ticket_action_kb, cancel_kb
from bot.utils.logger import log_event

router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        f"Привет! Это бот техподдержки **🏝{SERVICE_NAME}**.\n"
        "Опишите вашу проблему в одном сообщении (можно с фото/видео), и мы создадим заявку.",
        parse_mode="HTML"
    )


@router.message(F.text == "❌ Отмена")
async def cmd_cancel(message: Message):
    await message.answer("Действие отменено.", reply_markup=ReplyKeyboardRemove())


@router.callback_query(F.data.startswith("solved_"))
async def feedback_handler(callback: CallbackQuery, bot: Bot):
    action, ticket_id = callback.data.split("_")[1], callback.data.split("_")[2]

    if action == "yes":
        await callback.message.edit_text(f"Заявка №{ticket_id} закрыта. Спасибо за обращение!")
        # Статус уже closed, ничего менять не надо
    else:
        # Переоткрываем
        await reopen_ticket_status(ticket_id)
        await callback.message.edit_text(f"Заявка №{ticket_id} переоткрыта. Оператор скоро вернется.")

        # Уведомляем админов
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id,
                                       f"⚠️ Пользователь не удовлетворен решением заявки №{ticket_id}. Она переоткрыта.")
            except:
                pass


@router.message(F.chat.type == "private")
async def handle_user_message(message: Message, bot: Bot, album: list[Message] = None):
    user_id = message.from_user.id

    # Проверяем, есть ли активный тикет
    active_ticket = await get_active_ticket(user_id)

    # --- СЦЕНАРИЙ 1: НОВЫЙ ТИКЕТ ---
    if not active_ticket:
        count = await count_active_tickets(user_id)
        if count >= 3:
            await message.answer("У вас уже 3 открытых заявки. Пожалуйста, дождитесь их решения.")
            return

        ticket_id = await create_ticket(user_id)
        await message.answer(f"✅ Заявка №{ticket_id} создана!\nОжидайте ответа оператора.", parse_mode="HTML")
        await log_event(bot, f"🆕 User {user_id} created Ticket #{ticket_id}")

        # Уведомляем админов
        text = (f"🆕 Новая заявка №{ticket_id}\n"
                f"От: {message.from_user.full_name} (@{message.from_user.username})\n"
                f"ID: {user_id}")

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, text, reply_markup=ticket_action_kb(ticket_id))
            except Exception:
                pass

        # Обновляем переменную, чтобы отправить контент ниже
        active_ticket = await get_active_ticket(user_id)

    # --- СЦЕНАРИЙ 2: ОТПРАВКА СООБЩЕНИЯ АДМИНУ ---
    ticket_id = active_ticket['id']
    admin_id = active_ticket['admin_id']

    # Если админ еще не взял заявку, сообщение просто копится (в чате админа уведомление о новой заявке висит)
    # Если хотим, чтобы пришло доп уведомление:
    if not admin_id:
        return

        # Пересылка контента админу
    try:
        msgs_to_process = album if album else [message]

        if album:
            mg = MediaGroupBuilder(caption=f"📨 Тикет #{ticket_id}")
            for m in msgs_to_process:
                if m.photo:
                    mg.add_photo(m.photo[-1].file_id)
                elif m.video:
                    mg.add_video(m.video.file_id)
                elif m.document:
                    mg.add_document(m.document.file_id)

            sent_msgs = await bot.send_media_group(admin_id, media=mg.build())
            # Сохраняем референс первого сообщения для Reply
            await save_message_ref(admin_id, sent_msgs[0].message_id, ticket_id)
        else:
            # Используем copy_message для анонимности (юзер не видит форварда)
            # НО нам надо переслать АДМИНУ сообщение ЮЗЕРА. Тут можно Forward, чтобы админ видел профиль.
            # По ТЗ: "Anonymity: Users must see messages from SERVICE_NAME".
            # Это касается User -> Admin или Admin -> User? Обычно Admin -> User.
            # User -> Admin обычно делается Forward, чтобы админ мог забанить если что.
            # Но сделаем copy_message для чистоты, добавив хедер.

            sent_msg = await bot.copy_message(
                chat_id=admin_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                caption=message.caption or message.text  # Сохраняем подпись
            )
            # Сохраняем связку: Это сообщение у админа относится к этому тикету
            await save_message_ref(admin_id, sent_msg.message_id, ticket_id)

    except Exception as e:
        await log_event(bot, f"❌ Ошибка доставки сообщения админу (Ticket {ticket_id}): {e}")