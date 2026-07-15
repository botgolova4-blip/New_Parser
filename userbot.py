import os
import asyncio
from pyrogram import Client
from pyrogram.errors import (
    FloodWait, SessionPasswordNeeded,
    PhoneCodeInvalid, PhoneCodeExpired,
)
from database import save_session, disconnect_session, clear_session, save_auth_state, get_auth_state, clear_auth_state

SESSION_NAME = "userbot_session"

_userbot: Client | None = None
_is_connected = False


def get_userbot() -> Client | None:
    return _userbot


def is_connected() -> bool:
    return _is_connected and _userbot is not None


async def start_userbot(api_id: int, api_hash: str) -> bool:
    global _userbot, _is_connected
    if _is_connected and _userbot:
        return True
    try:
        _userbot = Client(SESSION_NAME, api_id=api_id, api_hash=api_hash)
        await _userbot.start()
        _is_connected = True
        return True
    except Exception:
        _userbot = None
        _is_connected = False
        return False


async def stop_userbot():
    global _userbot, _is_connected
    if _userbot:
        try:
            await _userbot.stop()
        except Exception:
            pass
    _userbot = None
    _is_connected = False
    await disconnect_session()


async def full_disconnect():
    await stop_userbot()
    await clear_session()
    await clear_auth_state()
    for ext in ("", ".session"):
        path = SESSION_NAME + ext
        if os.path.exists(path):
            os.remove(path)


async def auth_send_code(phone: str, api_id: int, api_hash: str) -> dict:
    for ext in ("", ".session"):
        path = SESSION_NAME + ext
        if os.path.exists(path):
            os.remove(path)

    try:
        client = Client(SESSION_NAME, api_id=api_id, api_hash=api_hash)
        await client.connect()
        sent = await client.send_code(phone)
        await client.disconnect()

        await save_auth_state(
            phone=phone,
            phone_code_hash=sent.phone_code_hash,
            api_id=str(api_id),
            api_hash=api_hash,
        )
        return {"ok": True}
    except FloodWait as e:
        return {"error": f"Слишком много попыток. Подождите {e.value} сек."}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)}"}


async def auth_sign_in(code: str) -> dict:
    global _userbot, _is_connected

    auth = await get_auth_state()
    if not auth:
        return {"error": "Сессия авторизации не найдена. Начните заново."}

    phone = auth["phone"]
    phone_code_hash = auth["phone_code_hash"]
    api_id = int(auth["api_id"])
    api_hash = auth["api_hash"]

    try:
        client = Client(SESSION_NAME, api_id=api_id, api_hash=api_hash)
        await client.connect()
        await client.sign_in(phone, phone_code_hash, code.replace(" ", ""))
        await client.disconnect()
        await clear_auth_state()

        await save_session(phone, str(api_id), api_hash)
        _userbot = Client(SESSION_NAME, api_id=api_id, api_hash=api_hash)
        await _userbot.start()
        _is_connected = True
        return {"ok": True}
    except SessionPasswordNeeded:
        return {"2fa": True}
    except (PhoneCodeInvalid, PhoneCodeExpired) as e:
        return {"error": f"[{type(e).__name__}] {str(e)} | hash: {phone_code_hash[:10]}..."}
    except Exception as e:
        return {"error": f"[{type(e).__name__}] {str(e)}"}


async def auth_check_password(password: str) -> dict:
    global _userbot, _is_connected

    auth = await get_auth_state()
    if not auth:
        return {"error": "Сессия авторизации не найдена. Начните заново."}

    api_id = int(auth["api_id"])
    api_hash = auth["api_hash"]
    phone = auth["phone"]

    try:
        client = Client(SESSION_NAME, api_id=api_id, api_hash=api_hash)
        await client.connect()
        await client.check_password(password)
        await client.disconnect()
        await clear_auth_state()

        await save_session(phone, str(api_id), api_hash)
        _userbot = Client(SESSION_NAME, api_id=api_id, api_hash=api_hash)
        await _userbot.start()
        _is_connected = True
        return {"ok": True}
    except Exception as e:
        return {"error": f"[{type(e).__name__}] {str(e)}"}
