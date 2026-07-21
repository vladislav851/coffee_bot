from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📦 Учёт склада", callback_data="menu_stock")],
        [InlineKeyboardButton(text="🍽 КБЖУ",         callback_data="menu_kbzhu")],
        [InlineKeyboardButton(text="🧹 Очистить чат", callback_data="clear_chat")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def stock_menu_keyboard(direction: str) -> InlineKeyboardMarkup:
    if direction == "warehouse_to_coffee":
        direction_label = "🔄 Направление: Склад → Кофейня"
    else:
        direction_label = "🔄 Направление: Кофейня → Склад"

    buttons = [
        [InlineKeyboardButton(text="📊 Все остатки",             callback_data="full_report")],
        [InlineKeyboardButton(text="📍 Остатки по локации",      callback_data="location_report_menu")],
        [InlineKeyboardButton(text="📋 Инвентаризация Склада",   callback_data="inventory_warehouse")],
        [InlineKeyboardButton(text="📋 Инвентаризация Кофейни",  callback_data="inventory_coffee_shop")],
        [InlineKeyboardButton(text=direction_label,              callback_data="toggle_direction")],
        [InlineKeyboardButton(text="↩️ Отменить последнее действие", callback_data="undo_last")],
        [InlineKeyboardButton(text="⬅️ Назад",                    callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def location_report_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🏬 Склад",  callback_data="location_report_warehouse")],
        [InlineKeyboardButton(text="☕ Кофейня", callback_data="location_report_coffee_shop")],
        [InlineKeyboardButton(text="⬅️ Назад",  callback_data="menu_stock")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kbzhu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def finish_inventory_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="✅ Завершить инвентаризацию", callback_data="finish_inventory")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
