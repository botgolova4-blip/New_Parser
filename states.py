from aiogram.fsm.state import State, StatesGroup


class AuthStates(StatesGroup):
    waiting_api_id    = State()   # шаг 1
    waiting_api_hash  = State()   # шаг 2
    waiting_phone     = State()   # шаг 3
    waiting_code      = State()   # шаг 4
    waiting_2fa       = State()   # шаг 5 (если есть)


class ParserStates(StatesGroup):
    waiting_channel   = State()
    waiting_mode_choice = State()
    waiting_count     = State()
    waiting_date_from = State()
    waiting_date_to   = State()
    confirming        = State()
