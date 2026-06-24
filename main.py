import asyncio
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart

from config import ADMIN_IDS
from db.database import (
    get_all_users, get_users_count, add_users,
    get_session_info,
)
from handlers.states import AuthStates, ParserStates
from handlers.keyboards import (
    main_menu_kb, parse_mode_kb, confirm_parse_kb,
    running_kb, done_kb, cancel_kb, disconnect_kb,
)
from utils import userbot as ub
from utils.parser import parse_channel

router = Router()


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


# ═══════════════════════════════════════════════════════════════════════════════
#  /start
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Нет доступа.")
    await message.answer(
        "👋 <b>Парсер Telegram</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=main_menu_kb(ub.is_connected()),
    )


# ── helpers ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer()
    await state.clear()
    await call.message.edit_text(
        "👋 <b>Парсер Telegram</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=main_menu_kb(ub.is_connected()),
    )


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()


# ═══════════════════════════════════════════════════════════════════════════════
#  ПОДКЛЮЧЕНИЕ АККАУНТА  (api_id → api_hash → phone → code → [2fa])
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "connect_account")
async def connect_account(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer()

    if ub.is_connected():
        session = await get_session_info()
        phone = session["phone"] if session else "неизвестен"
        await call.message.edit_text(
            f"✅ <b>Аккаунт подключён</b>\n"
            f"📱 Номер: <code>{phone}</code>\n\n"
            f"Хотите переподключить другой аккаунт — нажмите «Отключить».",
            parse_mode="HTML",
            reply_markup=disconnect_kb(),
        )
        return

    await call.message.edit_text(
        "🔑 <b>Шаг 1 из 4 — API ID</b>\n\n"
        "Введите ваш <b>API ID</b>.\n\n"
        "Где взять:\n"
        "1. Откройте my.telegram.org\n"
        "2. Войдите в аккаунт\n"
        "3. Перейдите в <b>API development tools</b>\n"
        "4. Скопируйте <b>App api_id</b> (число)\n\n"
        "<i>Эти данные хранятся только у вас в боте.</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await state.set_state(AuthStates.waiting_api_id)


@router.message(AuthStates.waiting_api_id)
async def got_api_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    raw = message.text.strip()
    if not raw.isdigit():
        return await message.answer("❌ API ID — это число. Попробуйте ещё раз:")
    await state.update_data(api_id=int(raw))
    await message.answer(
        "🔑 <b>Шаг 2 из 4 — API Hash</b>\n\n"
        "Введите ваш <b>API Hash</b> (строка из букв и цифр):",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await state.set_state(AuthStates.waiting_api_hash)


@router.message(AuthStates.waiting_api_hash)
async def got_api_hash(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    raw = message.text.strip()
    if len(raw) < 10:
        return await message.answer("❌ Слишком короткий API Hash. Проверьте и введите снова:")
    await state.update_data(api_hash=raw)
    await message.answer(
        "📱 <b>Шаг 3 из 4 — Номер телефона</b>\n\n"
        "Введите номер в международном формате:\n"
        "<code>+79001234567</code>",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await state.set_state(AuthStates.waiting_phone)


@router.message(AuthStates.waiting_phone)
async def got_phone(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    phone = message.text.strip()
    data = await state.get_data()
    msg = await message.answer("⏳ Отправляю код на номер...")

    result = await ub.auth_send_code(
        phone=phone,
        api_id=data["api_id"],
        api_hash=data["api_hash"],
    )

    if result.get("ok"):
        await state.update_data(phone=phone)
        await state.set_state(AuthStates.waiting_code)
        await msg.edit_text(
            f"📨 <b>Шаг 4 из 4 — Код подтверждения</b>\n\n"
            f"Код отправлен на <code>{phone}</code>.\n"
            f"Введите его (можно с пробелами: <code>1 2 3 4 5</code>):",
            parse_mode="HTML",
        )
    else:
        await msg.edit_text(f"❌ Ошибка: {result['error']}")


@router.message(AuthStates.waiting_code)
async def got_code(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    code = message.text.strip()
    msg = await message.answer("⏳ Проверяю код...")
    result = await ub.auth_sign_in(code)

    if result.get("ok"):
        await state.clear()
        await msg.edit_text(
            "✅ <b>Аккаунт успешно подключён!</b>",
            parse_mode="HTML",
            reply_markup=main_menu_kb(True),
        )
    elif result.get("2fa"):
        await state.set_state(AuthStates.waiting_2fa)
        await msg.edit_text(
            "🔐 <b>Двухфакторная аутентификация</b>\n\n"
            "Введите ваш пароль Telegram:",
            parse_mode="HTML",
        )
    else:
        await msg.edit_text(f"❌ {result['error']}\n\nПопробуйте ввести код снова:")


@router.message(AuthStates.waiting_2fa)
async def got_2fa(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    msg = await message.answer("⏳ Проверяю пароль...")
    result = await ub.auth_check_password(message.text.strip())
    if result.get("ok"):
        await state.clear()
        await msg.edit_text(
            "✅ <b>Аккаунт успешно подключён!</b>",
            parse_mode="HTML",
            reply_markup=main_menu_kb(True),
        )
    else:
        await msg.edit_text(f"❌ {result['error']}\n\nПопробуйте ещё раз:")


@router.callback_query(F.data == "disconnect_account")
async def disconnect_account(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer()
    await ub.full_disconnect()
    await call.message.edit_text(
        "🔌 <b>Аккаунт отключён.</b>\n\n"
        "Сессия и данные удалены. Можете подключить другой аккаунт.",
        parse_mode="HTML",
        reply_markup=main_menu_kb(False),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  РЕЗУЛЬТАТЫ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "show_results")
async def show_results(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer()
    count = await get_users_count()
    if count == 0:
        return await call.message.edit_text(
            "📭 База пуста. Запустите парсинг.",
            reply_markup=main_menu_kb(ub.is_connected()),
        )
    users = await get_all_users()
    if count <= 100:
        await call.message.edit_text(
            f"📋 <b>Спаршено: {count} пользователей</b>\n\n" + "\n".join(users),
            parse_mode="HTML",
            reply_markup=main_menu_kb(ub.is_connected()),
        )
    else:
        file_bytes = "\n".join(users).encode("utf-8")
        doc = BufferedInputFile(file_bytes, filename=f"parsed_{count}.txt")
        await call.message.answer_document(
            doc,
            caption=f"📋 Всего в базе: <b>{count}</b> уникальных пользователей",
            parse_mode="HTML",
        )
        await call.message.edit_reply_markup(
            reply_markup=main_menu_kb(ub.is_connected())
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  ПАРСИНГ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "start_parsing")
async def start_parsing(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer()
    if not ub.is_connected():
        return await call.answer("⚠️ Сначала подключите аккаунт!", show_alert=True)
    await call.message.edit_text(
        "🔗 <b>Ссылка на канал</b>\n\n"
        "Введите ссылку или @username канала:\n"
        "<code>https://t.me/channelname</code>\n"
        "<code>@channelname</code>",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await state.set_state(ParserStates.waiting_channel)


@router.message(ParserStates.waiting_channel)
async def got_channel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(channel=message.text.strip())
    await state.set_state(ParserStates.waiting_mode_choice)
    await message.answer(
        f"📡 Канал: <code>{message.text.strip()}</code>\n\n"
        "Выберите режим парсинга:",
        parse_mode="HTML",
        reply_markup=parse_mode_kb(),
    )


# ── count mode ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "mode_count")
async def mode_count(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer()
    await state.set_state(ParserStates.waiting_count)
    await call.message.edit_text(
        "🔢 <b>Количество постов</b>\n\n"
        "Введите число:\n\n"
        "• <code>10</code> — парсить последние 10 постов\n"
        "• <code>-10, 5</code> — пропустить 10 самых свежих, "
        "затем парсить следующие 5\n"
        "  <i>(т.е. посты с 11-го по 15-й от конца)</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(ParserStates.waiting_count)
async def got_count(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    value = message.text.strip()
    try:
        if "," in value:
            parts = value.split(",")
            skip = int(parts[0].strip())
            take = int(parts[1].strip())
            assert take > 0
            summary = f"Пропустить {abs(skip)} свежих → парсить следующие {take}"
        else:
            n = int(value)
            assert n > 0
            summary = f"Последние {n} постов"
    except Exception:
        return await message.answer(
            "❌ Неверный формат.\n"
            "Введите число (<code>10</code>) или диапазон (<code>-10, 5</code>)",
            parse_mode="HTML",
        )
    await state.update_data(mode="count", count_value=value)
    data = await state.get_data()
    await state.set_state(ParserStates.confirming)
    await message.answer(
        f"✅ <b>Настройки</b>\n\n"
        f"📡 Канал: <code>{data['channel']}</code>\n"
        f"📌 Режим: {summary}\n\n"
        f"Нажмите «Запустить»:",
        parse_mode="HTML",
        reply_markup=confirm_parse_kb(),
    )


# ── date mode ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "mode_dates")
async def mode_dates(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer()
    await state.set_state(ParserStates.waiting_date_from)
    await call.message.edit_text(
        "📅 <b>Диапазон дат — начало</b>\n\n"
        "Введите дату начала (<code>ДД.ММ.ГГГГ</code>):\n"
        "Пример: <code>01.01.2024</code>",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(ParserStates.waiting_date_from)
async def got_date_from(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        dt = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except ValueError:
        return await message.answer("❌ Формат: <code>ДД.ММ.ГГГГ</code>", parse_mode="HTML")
    await state.update_data(date_from=dt.isoformat())
    await state.set_state(ParserStates.waiting_date_to)
    await message.answer(
        "📅 <b>Диапазон дат — конец</b>\n\n"
        "Введите дату конца (<code>ДД.ММ.ГГГГ</code>):",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(ParserStates.waiting_date_to)
async def got_date_to(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        dt = datetime.fromisoformat((await state.get_data())["date_from"])
        dt_to = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except ValueError:
        return await message.answer("❌ Формат: <code>ДД.ММ.ГГГГ</code>", parse_mode="HTML")
    await state.update_data(mode="dates", date_to=dt_to.isoformat())
    data = await state.get_data()
    d_from = datetime.fromisoformat(data["date_from"]).strftime("%d.%m.%Y")
    d_to = dt_to.strftime("%d.%m.%Y")
    await state.set_state(ParserStates.confirming)
    await message.answer(
        f"✅ <b>Настройки</b>\n\n"
        f"📡 Канал: <code>{data['channel']}</code>\n"
        f"📅 Период: {d_from} — {d_to}\n\n"
        f"Нажмите «Запустить»:",
        parse_mode="HTML",
        reply_markup=confirm_parse_kb(),
    )


# ── run ───────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "run_parser")
async def run_parser(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer()

    data = await state.get_data()
    await state.clear()

    channel     = data.get("channel", "")
    mode        = data.get("mode", "count")
    count_value = data.get("count_value")
    date_from   = datetime.fromisoformat(data["date_from"]) if data.get("date_from") else None
    date_to     = datetime.fromisoformat(data["date_to"])   if data.get("date_to")   else None

    status_msg = await call.message.edit_text(
        "⏳ <b>Парсер запущен...</b>\n\nСобираю посты и комментарии.",
        parse_mode="HTML",
        reply_markup=running_kb(),
    )

    try:
        async def progress(info):
            if isinstance(info, str) and info.startswith("post_"):
                cur, total = info.split("_")[1].split("/")
                try:
                    await status_msg.edit_text(
                        f"⏳ <b>В работе...</b>\n\n📄 Пост {cur} из {total}",
                        parse_mode="HTML",
                        reply_markup=running_kb(),
                    )
                except Exception:
                    pass

        raw = await parse_channel(
            channel=channel,
            mode=mode,
            count_value=count_value,
            date_from=date_from,
            date_to=date_to,
            progress_callback=progress,
        )

        new_users = await add_users(raw)
        total_db  = await get_users_count()

        if not new_users:
            text = (
                f"✅ <b>Парсинг завершён</b>\n\n"
                f"Найдено пользователей: {len(raw)}\n"
                f"Новых (не в базе): <b>0</b>\n"
                f"Всего в базе: {total_db}\n\n"
                f"Все уже были в базе."
            )
        else:
            preview = "\n".join(new_users[:100])
            suffix  = f"\n…ещё {len(new_users)-100}" if len(new_users) > 100 else ""
            text = (
                f"✅ <b>Парсинг завершён</b>\n\n"
                f"Найдено: {len(raw)} | Новых: <b>{len(new_users)}</b> | В базе: {total_db}\n\n"
                f"<b>Новые пользователи:</b>\n{preview}{suffix}"
            )

        await status_msg.edit_text(text, parse_mode="HTML", reply_markup=done_kb())

        if len(new_users) > 100:
            doc = BufferedInputFile(
                "\n".join(new_users).encode(),
                filename=f"new_users_{len(new_users)}.txt",
            )
            await call.message.answer_document(
                doc,
                caption=f"📄 Полный список новых ({len(new_users)} шт.)",
            )

    except Exception as e:
        await status_msg.edit_text(
            f"❌ <b>Ошибка:</b>\n<code>{e}</code>",
            parse_mode="HTML",
            reply_markup=done_kb(),
        )
