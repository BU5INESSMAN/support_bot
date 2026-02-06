from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.utils.media_group import MediaGroupBuilder
from bot.database import create_ticket, get_active_ticket, save_message_ref
from bot.config import ADMIN_IDS, SERVICE_NAME
from bot.keyboards import ticket_take_kb, admin_main_menu
from bot.utils.logger import log_event

router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("🛠 Панель администратора активирована.", reply_markup=admin_main_menu())
    else:
        await message.answer(f"Привет! Это <b>{SERVICE_NAME}</b>. Опишите вашу проблему:", parse_mode="HTML")


@router.message(F.chat.type == "private")
async def handle_user_message(message: Message, bot: Bot, album: list[Message] = None):
    # Игнорируем сообщения от админов, чтобы они не создавали тикеты сами себе
    if message.from_user.id in ADMIN_IDS:
        return

    active_ticket = await get_active_ticket(message.from_user.id)

    if not active_ticket:
        ticket_id = await create_ticket(message.from_user.id)
        await message.answer(f"✅ Заявка №{ticket_id} создана. Ожидайте ответа.")

        # Уведомляем админов о новой заявке
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🆕 Новая заявка №{ticket_id} от @{message.from_user.username}",
                    reply_markup=ticket_take_kb(ticket_id)
                )
            except:
                pass
        active_ticket = await get_active_ticket(message.from_user.id)

    admin_id = active_ticket['admin_id']
    if not admin_id:
        return  # Заявка создана, но еще не принята админом

    # Пересылка контента (текст или медиа)
    try:
        if album:
            mg = MediaGroupBuilder(caption=f"📨 Тикет #{active_ticket['id']}")
            for m in album:
                if m.photo:
                    mg.add_photo(m.photo[-1].file_id)
                elif m.video:
                    mg.add_video(m.video.file_id)
                elif m.document:
                    mg.add_document(m.document.file_id)
            sent_msgs = await bot.send_media_group(admin_id, media=mg.build())
            await save_message_ref(admin_id, sent_msgs[0].message_id, active_ticket['id'])
        else:
            sent = await bot.copy_message(admin_id, message.chat.id, message.message_id)
            await save_message_ref(admin_id, sent.message_id, active_ticket['id'])
    except Exception as e:
        await log_event(bot, f"Ошибка пересылки контента: {e}")