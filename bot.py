import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db, get_session_info
from handlers_main import router
from userbot import start_userbot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    await init_db()
    logger.info("DB ready")

    session = await get_session_info()
    if session and session.get("connected") and session.get("api_id"):
        ok = await start_userbot(
            api_id=int(session["api_id"]),
            api_hash=session["api_hash"],
        )
        logger.info("Userbot restored: %s", ok)

    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    logger.info("Polling started")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
