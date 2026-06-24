import aiosqlite
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS parsed_users (
                username TEXT PRIMARY KEY,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS userbot_session (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                phone    TEXT,
                api_id   TEXT,
                api_hash TEXT,
                connected INTEGER DEFAULT 0
            )
        """)
        await db.commit()


async def add_users(usernames: list) -> list:
    new_users = []
    async with aiosqlite.connect(DB_PATH) as db:
        for username in usernames:
            username = username.lower().strip()
            if not username:
                continue
            cursor = await db.execute(
                "SELECT 1 FROM parsed_users WHERE username = ?", (username,)
            )
            if not await cursor.fetchone():
                await db.execute(
                    "INSERT OR IGNORE INTO parsed_users (username) VALUES (?)", (username,)
                )
                new_users.append(username)
        await db.commit()
    return new_users


async def get_all_users() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT username FROM parsed_users ORDER BY added_at DESC"
        )
        rows = await cursor.fetchall()
    return [r[0] for r in rows]


async def get_users_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM parsed_users")
        row = await cursor.fetchone()
    return row[0] if row else 0


async def save_session(phone: str, api_id: str, api_hash: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO userbot_session (id, phone, api_id, api_hash, connected)
            VALUES (1, ?, ?, ?, 1)
            ON CONFLICT(id) DO UPDATE SET
                phone    = excluded.phone,
                api_id   = excluded.api_id,
                api_hash = excluded.api_hash,
                connected = 1
        """, (phone, api_id, api_hash))
        await db.commit()


async def get_session_info() -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT phone, api_id, api_hash, connected FROM userbot_session WHERE id = 1"
        )
        row = await cursor.fetchone()
    if row:
        return {"phone": row[0], "api_id": row[1], "api_hash": row[2], "connected": bool(row[3])}
    return None


async def disconnect_session():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE userbot_session SET connected = 0 WHERE id = 1")
        await db.commit()


async def clear_session():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM userbot_session WHERE id = 1")
        await db.commit()
