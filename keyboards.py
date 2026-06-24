from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb(is_connected: bool) -> InlineKeyboardMarkup:
    connect_text = "✅ Аккаунт подключён" if is_connected else "🔗 Подключить аккаунт"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=connect_text, callback_data="connect_account")],
        [InlineKeyboardButton(text="🚀 Начать парсинг", callback_data="start_parsing")],
        [InlineKeyboardButton(text="📋 Результаты парсинга", callback_data="show_results")],
    ])


def parse_mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Указать диапазон дат", callback_data="mode_dates")],
        [InlineKeyboardButton(text="🔢 Указать количество постов", callback_data="mode_count")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])


def confirm_parse_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Запустить", callback_data="run_parser")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])


def running_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ В работе...", callback_data="noop")],
    ])


def done_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершено", callback_data="noop")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")],
    ])


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_main")],
    ])


def disconnect_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔌 Отключить аккаунт", callback_data="disconnect_account")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])
