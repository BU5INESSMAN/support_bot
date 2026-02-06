from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import math


def admin_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Открытые заявки"), KeyboardButton(text="Архив заявок")]
    ], resize_keyboard=True)


def user_cancel_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)


def ticket_take_kb(ticket_id):
    """Функция забора заявки (была ticket_action_kb)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✋ Забрать заявку", callback_data=f"take_{ticket_id}")]
    ])


def tickets_list_kb(tickets: list, page: int, total_count: int, status: str):
    builder = []
    for t in tickets:
        # Обработка того, что t может быть объектом Row или словарем
        t_id = t['id'] if isinstance(t, dict) or hasattr(t, '__getitem__') else t.id
        builder.append([InlineKeyboardButton(text=f"Заявка №{t_id}", callback_data=f"view_{t_id}")])

    total_pages = math.ceil(total_count / 10)
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"list_{status}_{page - 1}"))

    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="none"))

    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"list_{status}_{page + 1}"))

    if nav_row:
        builder.append(nav_row)
    return InlineKeyboardMarkup(inline_keyboard=builder)


def feedback_kb(ticket_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data=f"solved_yes_{ticket_id}"),
         InlineKeyboardButton(text="❌ Нет", callback_data=f"solved_no_{ticket_id}")]
    ])