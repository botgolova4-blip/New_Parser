from aiogram.fsm.state import State, StatesGroup


class AuthStates(StatesGroup):
    waiting_api_id   = State()
    waiting_api_hash = State()
    waiting_code     = State()   # session string


class ParserStates(StatesGroup):
    waiting_channel_choice = State()
    waiting_channel_link   = State()
    waiting_topic_choice   = State()  # выбор темы форума
    waiting_mode_choice    = State()
    waiting_count          = State()
    waiting_date_from      = State()
    waiting_date_to        = State()
    confirming             = State()
