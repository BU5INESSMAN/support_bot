from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.utils.media_group import MediaGroupBuilder

from bot.database import (
    get_ticket, update_ticket_admin, get_ticket_by_ref,
    close_ticket_status
)
from bot.keyboards import feedback_kb
from bot.utils.logger import log_event

router = Router()


@router.callback_query(F.data.startswith("take_"))
async def take_ticket_handler(callback: CallbackQuery, bot: Bot):
    ticket_id = int(callback.data.split("_")[1])
    ticket = await get_ticket(ticket_id)

    if ticket['admin_id']:
        await callback.answer("Заявку уже кто-то взял!", show_alert=True)
        return

    await update_ticket_admin(ticket_id, callback.from_user.id)

    # Обновляем сообщение у админа
    await callback.message.edit_text(
        f"✅ Заявку №{ticket_id} взял @{callback.from_user.username}",
        parse_mode="HTML"
    )

    # Уведомляем юзера
    try:
        await bot.send_message(ticket['user_id'], f"👨‍💻 Администратор подключился к заявке №{ticket_id}.")
    except:
        pass

    await log_event(bot, f"Admin {callback.from_user.id} took ticket #{ticket_id}")


# Обработка ответов админа (Reply)
@router.message(F.reply_to_message)
async def admin_reply_to_ticket(message: Message, bot: Bot, album: list[Message] = None):
    # Пытаемся найти тикет по сообщению, на которое ответили
    ref_id = message.reply_to_message.message_id
    ticket_id = await get_ticket_by_ref(message.chat.id, ref_id)

    if not ticket_id:
        return  # Это просто общение админов между собой

    ticket = await get_ticket(ticket_id)
    if ticket['status'] != 'open':
        await message.answer("⚠️ Заявка закрыта. Чтобы написать пользователю, он должен создать новую.")
        return

    # Логика закрытия заявки через команду /close
    if message.text == "/close":
        await close_ticket_status(ticket_id)
        await message.answer(f"🏁 Заявка №{ticket_id} закрыта.")
        try:
            await bot.send_message(
                ticket['user_id'],
                f"Ваша заявка №{ticket_id} закрыта.\nВаша проблема решена?",
                reply_markup=feedback_kb(ticket_id)
            )
        except:
            pass
        await log_event(bot, f"Admin {message.from_user.id} closed ticket #{ticket_id}")
        return

    # Отправка ответа пользователю (Анонимно, через копирование)
    try:
        user_id = ticket['user_id']
        msgs = album if album else [message]

        if album:
            mg = MediaGroupBuilder()
            for m in msgs:
                if m.photo:
                    mg.add_photo(m.photo[-1].file_id)
                elif m.document:
                    mg.add_document(m.document.file_id)
            await bot.send_media_group(user_id, media=mg.build())
        else:
            await message.copy_to(chat_id=user_id)

    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")