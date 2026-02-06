from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def cancel_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="❌ Отмена")]
    ], resize_keyboard=True, one_time_keyboard=True)

def ticket_action_kb(ticket_id):
    """Кнопка для админов 'Взять заявку'"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✋ Забрать заявку", callback_data=f"take_{ticket_id}")]
    ])

def feedback_kb(ticket_id):
    """Кнопки 'Решена ли проблема?'"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data=f"solved_yes_{ticket_id}"),
         InlineKeyboardButton(text="❌ Нет", callback_data=f"solved_no_{ticket_id}")]
    ])