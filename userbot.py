import os
from pyrogram import Client
from pyrogram.errors import (
    FloodWait, SessionPasswordNeeded,
    PhoneCodeInvalid, PhoneCodeExpired,
)
from db.database import save_session, disconnect_session, clear_session

SESSION_NAME = "userbot_session"

# ── live userbot ──────────────────────────────────────────────────────────────
_userbot: Client | None = None
_is_connected = False


def get_userbot() -> Client | None:
    return _userbot


def is_connected() -> bool:
    return _is_connected and _userbot is not None


async def start_userbot(api_id: int, api_hash: str) -> bool:
    """Start userbot from saved session file (no phone re-auth needed)."""
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
    """Stop + wipe session file + wipe DB record."""
    await stop_userbot()
    await clear_session()
    for ext in ("", ".session"):
        path = SESSION_NAME + ext
        if os.path.exists(path):
            os.remove(path)


# ── auth flow (step-by-step inside bot) ──────────────────────────────────────
_auth_client: Client | None = None
_auth_phone: str | None = None
_auth_phone_code_hash: str | None = None
_auth_api_id: int | None = None
_auth_api_hash: str | None = None


async def auth_send_code(phone: str, api_id: int, api_hash: str) -> dict:
    global _auth_client, _auth_phone, _auth_phone_code_hash
    global _auth_api_id, _auth_api_hash

    # Clean up any old partial session file so Pyrogram starts fresh
    for ext in ("", ".session"):
        path = SESSION_NAME + ext
        if os.path.exists(path):
            os.remove(path)

    try:
        _auth_client = Client(SESSION_NAME, api_id=api_id, api_hash=api_hash)
        await _auth_client.connect()
        sent = await _auth_client.send_code(phone)
        _auth_phone = phone
        _auth_phone_code_hash = sent.phone_code_hash
        _auth_api_id = api_id
        _auth_api_hash = api_hash
        return {"ok": True}
    except FloodWait as e:
        return {"error": f"Слишком много попыток. Подождите {e.value} сек."}
    except Exception as e:
        return {"error": str(e)}


async def auth_sign_in(code: str) -> dict:
    global _auth_client, _userbot, _is_connected
    if not _auth_client or not _auth_phone:
        return {"error": "Сначала отправьте номер телефона"}
    try:
        await _auth_client.sign_in(
            _auth_phone, _auth_phone_code_hash, code.replace(" ", "")
        )
        await _auth_client.disconnect()
        _auth_client = None

        # Persist & start live userbot
        await save_session(_auth_phone, str(_auth_api_id), _auth_api_hash)
        _userbot = Client(SESSION_NAME, api_id=_auth_api_id, api_hash=_auth_api_hash)
        await _userbot.start()
        _is_connected = True
        return {"ok": True}
    except SessionPasswordNeeded:
        return {"2fa": True}
    except (PhoneCodeInvalid, PhoneCodeExpired):
        return {"error": "Неверный или истёкший код. Попробуйте снова."}
    except Exception as e:
        return {"error": str(e)}


async def auth_check_password(password: str) -> dict:
    global _auth_client, _userbot, _is_connected
    if not _auth_client:
        return {"error": "Сессия авторизации не найдена"}
    try:
        await _auth_client.check_password(password)
        await _auth_client.disconnect()
        _auth_client = None

        await save_session(_auth_phone, str(_auth_api_id), _auth_api_hash)
        _userbot = Client(SESSION_NAME, api_id=_auth_api_id, api_hash=_auth_api_hash)
        await _userbot.start()
        _is_connected = True
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}
