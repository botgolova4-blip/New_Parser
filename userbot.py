import os
from pyrogram import Client
from database import save_session, disconnect_session, clear_session, get_session_info

SESSION_NAME = "userbot_session"

_userbot: Client | None = None
_is_connected = False


def get_userbot() -> Client | None:
    return _userbot


def is_connected() -> bool:
    return _is_connected and _userbot is not None


async def start_userbot_from_string(session_string: str, api_id: int, api_hash: str) -> bool:
    global _userbot, _is_connected
    try:
        _userbot = Client(
            name=SESSION_NAME,
            api_id=api_id,
            api_hash=api_hash,
            session_string=session_string,
        )
        await _userbot.start()
        me = await _userbot.get_me()
        _is_connected = True
        await save_session(
            phone=me.phone_number or "unknown",
            api_id=str(api_id),
            api_hash=api_hash,
        )
        return True
    except Exception as e:
        _userbot = None
        _is_connected = False
        return False


async def start_userbot(api_id: int, api_hash: str) -> bool:
    """Restore from session string env var or saved session file."""
    global _userbot, _is_connected
    if _is_connected and _userbot:
        return True

    session_string = os.getenv("SESSION_STRING", "").strip()
    if session_string:
        return await start_userbot_from_string(session_string, api_id, api_hash)

    # Fallback: try session file
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
    for ext in ("", ".session"):
        path = SESSION_NAME + ext
        if os.path.exists(path):
            os.remove(path)


# ── Авторизация через session string (из бота) ────────────────────────────────

async def auth_via_session_string(session_string: str, api_id: int, api_hash: str) -> dict:
    """Connect using a pre-generated session string."""
    global _userbot, _is_connected
    try:
        client = Client(
            name=SESSION_NAME,
            api_id=api_id,
            api_hash=api_hash,
            session_string=session_string,
        )
        await client.start()
        me = await client.get_me()
        _userbot = client
        _is_connected = True
        await save_session(
            phone=me.phone_number or "unknown",
            api_id=str(api_id),
            api_hash=api_hash,
        )
        return {"ok": True, "name": me.first_name, "phone": me.phone_number}
    except Exception as e:
        return {"error": f"[{type(e).__name__}] {str(e)}"}
