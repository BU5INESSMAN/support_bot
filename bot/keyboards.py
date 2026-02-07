from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import math
from aiogram.utils.keyboard import InlineKeyboardBuilder


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


# Добавь в bot/keyboards.py
from aiogram.utils.keyboard import InlineKeyboardBuilder
import math


def tickets_list_kb(tickets, page, total_count, status):
    builder = InlineKeyboardBuilder()

    # Кнопки заявок
    for t in tickets:
        builder.button(text=f"🎫 №{t['id']}", callback_data=f"view_{t['id']}")

    builder.adjust(2)  # Список заявок в 2 колонки

    # Ряд навигации
    nav_buttons = []
    total_pages = math.ceil(total_count / 10)

    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"list_{status}_{page - 1}"))

    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="none"))

    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"list_{status}_{page + 1}"))

    if nav_buttons:
        builder.row(*nav_buttons)

    return builder.as_markup()


def feedback_kb(ticket_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data=f"solved_yes_{ticket_id}"),
         InlineKeyboardButton(text="❌ Нет", callback_data=f"solved_no_{ticket_id}")]
    ])

def ticket_view_kb(ticket_id):
    """Клавиатура с кнопкой просмотра истории переписки"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Просмотреть переписку", callback_data=f"history_{ticket_id}")]
    ])
