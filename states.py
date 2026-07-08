from aiogram.fsm.state import State, StatesGroup


class AuthStates(StatesGroup):
    waiting_api_id   = State()
    waiting_api_hash = State()
    waiting_phone    = State()
    waiting_code     = State()
    waiting_2fa      = State()


class ParserStates(StatesGroup):
    waiting_channel_choice = State()  # выбор способа: список или ссылка
    waiting_channel_link   = State()  # ввод ссылки вручную
    waiting_mode_choice    = State()  # выбор режима парсинга
    waiting_count          = State()
    waiting_date_from      = State()
    waiting_date_to        = State()
    confirming             = State()
