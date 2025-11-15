"""Application handlers — minimal, UI-first.

Что изменено:
  1) /start ловим как on_message("start") с корректной сигнатурой Message.
  3) Единая проверка разрешения на смену роли (_can_change_role).
  4) Смена состояний через bot.storage.change_state().
  5) Предикат is_state() для лаконичных фильтров.

Новое:
  • Хендлер 'feed' показывает ленту с действиями.
  • Кнопки 'change_city' и 'change_filters' переводят в те же стейты,
    что и при регистрации, но с флагом «вернуться к ленте».
  • После успешного ввода города/интересов, если флаг активен —
    возвращаем пользователя в ленту, иначе ведём как раньше.
  • Хендлер 'details_1' показывает детали заявки с кнопками действий.
  • Хендлер 'respond' обрабатывает отклик волонтёра на заявку.
"""
from __future__ import annotations

import os
import logging
from typing import Callable, Awaitable, Any

import aiomax

from app.keyboards.inline_keyboards import (
    role_selection_keyboard,
    volunteer_main_menu_keyboard,
    profile_keyboard,
    event_item_keyboard,
    fund_item_keyboard,
    feed_actions_keyboard,
    request_details_keyboard,
    response_confirmation_keyboard,
    donation_confirmation_keyboard,
    admin_fund_main_keyboard,
    admin_event_created_keyboard,
    admin_help_keyboard,
    application_moderation_keyboard,
    my_applications_return_keyboard,
)
from app.states import VolunteerStates, HelpRequestStates, CommonStates, AdminStates
from app.services.role_stub import get_role, set_role, MOCK_FEED_MESSAGE, MOCK_REQUEST_DETAILS
from app.services.backend_client import backend_client
from app.services.session_store import set_session_token, get_session_token

# Логгер для отслеживания аутентификации и стартовых событий
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")


# =========================
# Конфигурация/константы
# =========================

WELCOME_MESSAGE = (
    "👋 Привет! Это демо интерфейса волонтёрского бота.\n\n"
    "Выберите роль, чтобы продолжить: \n"
    "• 🙋 Нужна помощь — сформировать заявку\n"
    "• 🤝 Хочу помочь — выбрать город и интересы\n\n"
    "Погнали! 🚀"
)

CITY_PROMPT_SUFFIX = (
    "Доступные города: 🏙️ Москва • 🏛️ Санкт-Петербург • 🏔️ Новосибирск"
)
MAX_CITIES_PAGE_SIZE = 100  # Ограничение бекенда (page_size <= 100)
INTERESTS_PROMPT_SUFFIX = (
    "Доступные интересы: 🌿 экология, 📚 образование, 🏥 медицина, 👶 дети, 🐾 животные"
)

# Разрешаем этому пользователю переизбирать роль (для тестов)
TEST_USER_ID = 89408765


# =========================
# Хелперы (п.п. 3 и 5)
# =========================

def _can_change_role(user_id: int) -> bool:
    """Повторный выбор роли: разрешён тестовому пользователю или тем, у кого роли ещё нет."""
    return user_id == TEST_USER_ID or not get_role(user_id)

def is_state(expected: str) -> Callable[[aiomax.Message], bool]:
    """Удобный предикат для on_message-фильтров по FSM-состоянию."""
    return lambda m: (m.bot.storage.get_state(m.user_id) == expected)


# =========================
# Внутренние утилиты (feed)
# =========================

# Простой флаг «после ввода вернуться к ленте». При желании перемести в role_stub/хранилище.
_RETURN_TO_FEED: dict[int, bool] = {}
_RETURN_TO_PROFILE: dict[int, bool] = {}
_FUND_FEED_CACHE: dict[int, dict[int, dict]] = {}  # user_id -> {fund_id: fund_dict}
_SELECTED_FUND: dict[int, int] = {}  # user_id -> fund_id (для доната)
_PENDING_EVENT_DATA: dict[int, dict] = {}  # временное хранение данных события до ввода города

def _set_return_to_feed(user_id: int) -> None:
    _RETURN_TO_FEED[user_id] = True

def _pop_return_to_feed(user_id: int) -> bool:
    """Вернёт True, если был запрошен возврат к ленте, и сразу сбросит флаг."""
    return _RETURN_TO_FEED.pop(user_id, False)

def _set_return_to_profile(user_id: int) -> None:
    _RETURN_TO_PROFILE[user_id] = True

def _has_return_to_profile(user_id: int) -> bool:
    return _RETURN_TO_PROFILE.get(user_id, False)

def _clear_return_to_profile(user_id: int) -> None:
    _RETURN_TO_PROFILE.pop(user_id, None)

async def _show_feed(send_callable: Callable[[str, Any | None], Awaitable[aiomax.Message]]) -> None:
    """Показ ленты с клавиатурой действий."""
    kb = feed_actions_keyboard()
    await send_callable(MOCK_FEED_MESSAGE, keyboard=kb)

async def _send_events_feed(
    user_id: int,
    send_callable: Callable[[str, Any | None], Awaitable[aiomax.Message]],
    page: int = 1,
    page_size: int = 5,
) -> None:
    """Получить ленту событий с бэкенда и отправить пользователю.

    Используется как в первоначальном переходе по кнопке 'Лента заявок', так и при возврате
    из подтверждения отклика / после изменения фильтров.
    """
    token = get_session_token(user_id)
    if not token:
        kb = volunteer_main_menu_keyboard()
        await send_callable(
            "⚠️ Нет активной сессии. Используйте /start и повторите запрос ленты.",
            keyboard=kb,
        )
        return

    include_tag_ids: list[int] | None = None
    try:
        profile = await backend_client.get_user_profile(token)
        interests = (profile.get("interests") or [])
        if interests:
            try:
                tags = await backend_client.get_tags(page=1, page_size=100)
                tag_map = {t.get("name", "").lower(): t.get("id") for t in tags}
                for interest in interests:
                    tid = tag_map.get(str(interest).lower())
                    if tid is not None:
                        include_tag_ids = [tid]
                        break
            except Exception as e_tags:
                logger.warning("Tags fetch failed (events_feed): user_id=%s error=%s", user_id, e_tags)
    except Exception as e_prof:
        logger.warning("Profile fetch failed (events_feed): user_id=%s error=%s", user_id, e_prof)

    events: list[dict] = []
    try:
        feed_resp = await backend_client.get_events_feed(
            token=token,
            include_tag_ids=include_tag_ids,
            page=page,
            page_size=page_size,
        )
        events = feed_resp.get("events") or []
    except Exception as e_feed:
        logger.warning("Events feed fetch failed (events_feed): user_id=%s error=%s", user_id, e_feed)

    if not events:
        kb = volunteer_main_menu_keyboard()
        await send_callable(
            "😕 События не найдены. Попробуйте позже или обновите интересы через 'Редактировать профиль'.",
            keyboard=kb,
        )
        return

    # Состояние ленты — сохраняем MAIN_MENU (навигационные кнопки работают)
    # Отправляем каждое событие отдельным сообщением
    for event in events:
        eid = event.get("id")
        title = event.get("title") or "—"
        description = event.get("description") or "—"
        address = event.get("address") or "—"
        what_to_do = event.get("what_to_do") or "—"
        text = (
            "📌 Мероприятие\n"
            "────────────────\n"
            f"🧷 ID: {eid}\n"
            f"📝 Название: {title}\n"
            f"📄 Описание: {description}\n"
            f"📍 Адрес: {address}\n"
            f"🛠️ Что делать: {what_to_do}\n"
            "────────────────\n"
            "Нажмите 'Откликнуться', если готовы помочь."
        )
        kb_item = event_item_keyboard()
        await send_callable(text, keyboard=kb_item)

async def _send_funds_feed(
    user_id: int,
    send_callable: Callable[[str, Any | None], Awaitable[aiomax.Message]],
    page: int = 1,
    page_size: int = 5,
) -> None:
    """Получить ленту фондов и отправить пользователю."""
    token = get_session_token(user_id)
    if not token:
        kb = volunteer_main_menu_keyboard()
        await send_callable(
            "⚠️ Нет активной сессии. Используйте /start и повторите запрос фондов.",
            keyboard=kb,
        )
        return

    funds: list[dict] = []
    try:
        feed_resp = await backend_client.get_funds_feed(
            token=token,
            page=page,
            page_size=page_size,
        )
        funds = feed_resp.get("funds") or []
    except Exception as e_feed:
        logger.warning("Funds feed fetch failed user_id=%s error=%s", user_id, e_feed)

    if not funds:
        kb = volunteer_main_menu_keyboard()
        await send_callable(
            "😕 Фонды не найдены. Попробуйте позже.",
            keyboard=kb,
        )
        return

    _FUND_FEED_CACHE[user_id] = {f.get("id"): f for f in funds if f.get("id") is not None}

    for fund in funds:
        fid = fund.get("id")
        title = fund.get("title") or "—"
        description = fund.get("description") or "—"
        target = fund.get("target_amount") or 0
        collected = fund.get("collected_amount") or 0
        rating_per_100 = fund.get("rating_per_100") or 0
        progress_pct = 0
        try:
            if target > 0:
                progress_pct = int((collected / target) * 100)
        except Exception:
            progress_pct = 0
        text = (
            "💰 Фонд помощи\n"
            "────────────────\n"
            f"🧷 ID: {fid}\n"
            f"📝 Название: {title}\n"
            f"📄 Описание: {description}\n"
            f"🎯 Цель: {target}₽\n"
            f"📦 Собрано: {collected}₽ ({progress_pct}%)\n"
            f"⭐ Рейтинг за 100₽: +{rating_per_100}\n"
            "────────────────\n"
            "Нажмите 'Пожертвовать', чтобы сделать вклад."
        )
        kb_item = fund_item_keyboard()
        await send_callable(text, keyboard=kb_item)

async def _render_profile(user_id: int, send_callable: Callable[[str, Any | None], Awaitable[aiomax.Message]]) -> None:
    """Формирование и отправка профиля (общая логика для просмотра и возврата после редактирования)."""
    token = get_session_token(user_id)
    kb = profile_keyboard()
    if not token:
        await send_callable(
            "⚠️ Профиль недоступен: нет активной сессии. Нажмите /start для повторной авторизации.",
            keyboard=kb
        )
        return
    city_name = "—"
    interests_text = "—"
    rating = 0
    participation_count = 0
    try:
        profile = await backend_client.get_user_profile(token)
        rating = profile.get("rating", 0)
        participation_count = profile.get("participation_count", 0)
        interests = profile.get("interests") or []
        if interests:
            interests_text = ", ".join(interests)
        city_id = profile.get("city_id")
        if city_id is not None:
            try:
                city = await backend_client.get_city(city_id)
                city_name = city.get("name") or f"ID {city_id}"
            except Exception as e_city:
                logger.warning("City fetch failed (render_profile): user_id=%s city_id=%s error=%s", user_id, city_id, e_city)
    except Exception as e_prof:
        logger.warning("Profile fetch failed (render_profile): user_id=%s error=%s", user_id, e_prof)
    text = (
        "👤 Профиль волонтёра\n"
        "────────────────────\n"
        f"🏙️ Город: {city_name}\n"
        f"🎯 Интересы: {interests_text}\n"
        f"📊 Рейтинг: {rating}\n"
        f"✅ Участий: {participation_count}\n"
        "────────────────────\n"
        "Чтобы обновить данные — кнопка 'Редактировать профиль'."
    )
    await send_callable(text, keyboard=kb)


# =========================
# Регистрация хендлеров
# =========================

def setup_handlers(bot: aiomax.Bot) -> None:

    # --- старт через текст "start" (для тестов) ---
    @bot.on_message("start")
    async def _start_message(msg: aiomax.Message, cursor: aiomax.FSMCursor):
        if not get_session_token(msg.user_id):
            logger.info("Auth attempt (message_start): user_id=%s username=%s", msg.user_id, msg.user.username)
            try:
                auth_res = await backend_client.login(
                    max_user_id=msg.user_id,
                    username=msg.user.username
                )
                token = auth_res["session_token"]
                set_session_token(msg.user_id, token)
                logger.info("Auth success (message_start): user_id=%s token_prefix=%s", msg.user_id, token[:10])
            except Exception as e:
                logger.exception("Auth failed (message_start): user_id=%s error=%s", msg.user_id, e)
        else:
            logger.info("Auth skip (message_start): existing token user_id=%s", msg.user_id)
        await _send_welcome(
            user_id=msg.user_id,
            send_callable=lambda text, keyboard=None: msg.reply(text, keyboard=keyboard),
        )
        msg.bot.storage.change_state(msg.user_id, CommonStates.IDLE)

    # --- платформенный старт (кнопка "Начать" в ЛС) ---
    
    @bot.on_bot_start()
    async def _on_start(payload: aiomax.BotStartPayload, cursor: aiomax.FSMCursor):
        # 1. Если у нас нет токена — логинимся
        if not get_session_token(payload.user.user_id):
            logger.info("Auth attempt (bot_start): user_id=%s username=%s", payload.user.user_id, payload.user.username)
            try:
                auth_res = await backend_client.login(
                    max_user_id=payload.user.user_id,
                    username=payload.user.username
                )
                token = auth_res["session_token"]
                set_session_token(payload.user.user_id, token)
                logger.info("Auth success (bot_start): user_id=%s token_prefix=%s", payload.user.user_id, token[:10])
            except Exception as e:
                logger.exception("Auth failed (bot_start): user_id=%s error=%s", payload.user.user_id, e)
        else:
            logger.info("Auth skip (bot_start): existing token user_id=%s", payload.user.user_id)
        # 2. Дальше текущая логика приветствия
        await _send_welcome(
            user_id=payload.user_id,
            send_callable=lambda text, keyboard=None: payload.send(text, keyboard=keyboard),
        )
        payload.bot.storage.change_state(payload.user_id, CommonStates.IDLE)

    # --- выбор роли: нужна помощь ---
    @bot.on_button_callback(lambda d: d.payload == "need_help")
    async def _need_help(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        """Инициировать процесс создания фонда для роли 'Нужна помощь'."""
        # Разрешаем повторный выбор для возможности добавить ещё фонды
        set_role(cb.user_id, "need_help")
        token = get_session_token(cb.user_id)
        role = None
        if token:
            try:
                role_info = await backend_client.check_user_role(token)
                if role_info:
                    role = role_info.get("role")
            except Exception as e_role:
                logger.warning("Check role failed user_id=%s error=%s", cb.user_id, e_role)
        if role != "admin" and token:
            try:
                created_admin = await backend_client.create_admin(token, cb.user_id)
                if created_admin:
                    role = "admin"
            except Exception as e_create_admin:
                logger.warning("Create admin attempt failed user_id=%s error=%s", cb.user_id, e_create_admin)
        cb.bot.storage.change_state(cb.user_id, HelpRequestStates.WAIT_FUND_INFO)
        await cb.send(
            "🏗️ Расскажите о своем фонде. Отправьте ОДНО сообщение в формате:\n"
            "Название\nОписание\nРеквизиты\nЦелевая_сумма\nРейтинг_за_100\nДата_окончания (YYYY-MM-DD или '-')\nТеги (например: 1,2,4)\n\n"
            "Теги: 1-экология 2-образование 3-медицина 4-дети 5-животные\n"
            "Пример:\nПомощь детям-сиротам\nСбор средств на образовательные программы для детей-сирот\nСБЕР 2202 2002 2002 2002\n100000\n1\n2024-12-31\n1,4,5"
        )

    # --- выбор роли: хочу помочь ---
    @bot.on_button_callback(lambda d: d.payload == "want_help")
    async def _want_help(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        if not _can_change_role(cb.user_id):
            return
        set_role(cb.user_id, "want_help")
        cb.bot.storage.change_state(cb.user_id, VolunteerStates.WAIT_CITY)
        await cb.send(
            f"🏙️ Укажите ваш город (одно сообщение).\n{CITY_PROMPT_SUFFIX}\n"
            "Формат: просто название, например: Москва"
        )

    # --- лента заявок ---
    @bot.on_button_callback(lambda d: d.payload == "feed")
    async def _feed(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        """Лента событий: получаем с бэкенда /events/feed и выводим каждое событие отдельным сообщением.

        Логика выбора тега:
        - Берём профиль пользователя -> список интересов (строки).
        - Берём список тегов и сопоставляем по имени (case-insensitive).
        - Берём первый совпавший тег как include_tags фильтр.
        - Если интересов нет или нет совпадений — отдаём ленту без фильтра (город пользователя).
        """
        cb.bot.storage.change_state(cb.user_id, VolunteerStates.MAIN_MENU)
        await _send_events_feed(cb.user_id, lambda text, keyboard=None: cb.send(text, keyboard=keyboard))

    # --- лента фондов ---
    @bot.on_button_callback(lambda d: d.payload == "funds")
    async def _funds(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        cb.bot.storage.change_state(cb.user_id, VolunteerStates.MAIN_MENU)
        await _send_funds_feed(cb.user_id, lambda text, keyboard=None: cb.send(text, keyboard=keyboard))

    # --- детали заявки 1 ---
    @bot.on_button_callback(lambda d: d.payload == "details_1")
    async def _details_1(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        """Обработчик кнопки 'Подробнее 1' — показываем детали заявки."""
        # TODO: backend.get_request_details(request_id=1)
        kb = request_details_keyboard()
        await cb.send(MOCK_REQUEST_DETAILS, keyboard=kb)

    # --- отклик на заявку ---
    @bot.on_button_callback(lambda d: d.payload == "respond")
    async def _respond(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        """Начало процесса отклика: просим ввести ID события из текущей ленты."""
        cb.bot.storage.change_state(cb.user_id, VolunteerStates.WAIT_EVENT_ID)
        await cb.send(
            "📝 Отправьте ID мероприятия, на которое хотите откликнуться (число).\n"
            "ID указан в блоке '🧷 ID: ...' выше."
        )

    # --- пожертвовать в фонд ---
    @bot.on_button_callback(lambda d: d.payload == "donate")
    async def _donate(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        cb.bot.storage.change_state(cb.user_id, VolunteerStates.WAIT_FUND_ID)
        await cb.send(
            "💸 Отправьте ID фонда, в который хотите пожертвовать (число).\n"
            "ID указан в блоке '🧷 ID: ...' в ленте фондов."
        )

    # --- ввод ID события для отклика ---
    @bot.on_message(is_state(VolunteerStates.WAIT_EVENT_ID))
    async def _volunteer_event_id(msg: aiomax.Message, cursor: aiomax.FSMCursor):
        raw = (getattr(msg, "text", None) or getattr(msg, "content", "") or "").strip()
        if not raw:
            await msg.reply("⚠️ Пусто. Введите числовой ID события.")
            return
        if not raw.isdigit():
            await msg.reply("❌ Нужно число. Попробуйте ещё раз (например: 12).")
            return
        event_id = int(raw)

        token = get_session_token(msg.user_id)
        if not token:
            msg.bot.storage.change_state(msg.user_id, VolunteerStates.MAIN_MENU)
            kb = volunteer_main_menu_keyboard()
            await msg.reply("⚠️ Нет активной сессии. /start", keyboard=kb)
            return

        # Проверим что событие действительно существует — запрос деталей
        event_details = None
        try:
            event_details = await backend_client.get_event_details(token, event_id)
        except Exception as e_event:
            logger.warning("Event details failed user_id=%s event_id=%s error=%s", msg.user_id, event_id, e_event)

        if not event_details:
            kb_err = response_confirmation_keyboard()
            await msg.reply(
                "❌ Событие с таким ID не найдено. Проверьте и введите снова или вернитесь к ленте.",
                keyboard=kb_err,
            )
            return

        # Создаём отклик
        created_app = None
        try:
            created_app = await backend_client.create_application(token, event_id)
        except Exception as e_create:
            logger.warning("Create application failed user_id=%s event_id=%s error=%s", msg.user_id, event_id, e_create)

        if not created_app:
            kb_err = response_confirmation_keyboard()
            await msg.reply(
                "❌ Не удалось создать отклик. Попробуйте позже или вернитесь к ленте.",
                keyboard=kb_err,
            )
            return

        # Готовим красивый ответ с деталями события
        contact = event_details.get("contact") or "—"
        date = event_details.get("date") or "—"
        address = event_details.get("address") or "—"
        what_to_do = event_details.get("what_to_do") or "—"
        title = event_details.get("title") or "—"

        text = (
            "✅ Спасибо за отклик! Ваша заявка на рассмотрении.\n"
            "────────────────────\n"
            f"🧷 ID события: {event_id}\n"
            f"📝 Название: {title}\n"
            f"☎️ Контакт: {contact}\n"
            f"🕒 Дата: {date}\n"
            f"📍 Адрес: {address}\n"
            f"🛠️ Что делать: {what_to_do}\n"
            "────────────────────\n"
            "Ожидайте подтверждения."
        )
        msg.bot.storage.change_state(msg.user_id, VolunteerStates.MAIN_MENU)
        kb = response_confirmation_keyboard()
        await msg.reply(text, keyboard=kb)

    # --- ввод ID фонда для доната ---
    @bot.on_message(is_state(VolunteerStates.WAIT_FUND_ID))
    async def _volunteer_fund_id(msg: aiomax.Message, cursor: aiomax.FSMCursor):
        raw = (getattr(msg, "text", None) or getattr(msg, "content", "") or "").strip()
        if not raw:
            await msg.reply("⚠️ Пусто. Введите числовой ID фонда.")
            return
        if not raw.isdigit():
            await msg.reply("❌ Нужно число. Попробуйте ещё раз (например: 3).")
            return
        fund_id = int(raw)

        token = get_session_token(msg.user_id)
        if not token:
            msg.bot.storage.change_state(msg.user_id, VolunteerStates.MAIN_MENU)
            kb = volunteer_main_menu_keyboard()
            await msg.reply("⚠️ Нет активной сессии. /start", keyboard=kb)
            return

        cached = _FUND_FEED_CACHE.get(msg.user_id) or {}
        if fund_id not in cached:
            kb_err = volunteer_main_menu_keyboard()
            await msg.reply(
                "❌ Фонд с таким ID не найден в последней ленте. Откройте 'Лента фондов' и попробуйте снова.",
                keyboard=kb_err,
            )
            return

        _SELECTED_FUND[msg.user_id] = fund_id
        msg.bot.storage.change_state(msg.user_id, VolunteerStates.WAIT_DONATION_AMOUNT)
        await msg.reply(
            "✅ Фонд выбран. Введите сумму пожертвования в рублях (целое число, > 0).\n"
            "Например: 500"
        )

    # --- ввод суммы доната ---
    @bot.on_message(is_state(VolunteerStates.WAIT_DONATION_AMOUNT))
    async def _volunteer_donation_amount(msg: aiomax.Message, cursor: aiomax.FSMCursor):
        raw = (getattr(msg, "text", None) or getattr(msg, "content", "") or "").strip()
        if not raw:
            await msg.reply("⚠️ Пусто. Введите сумму (число).")
            return
        if not raw.isdigit():
            await msg.reply("❌ Нужно целое число. Попробуйте ещё раз (например: 750).")
            return
        amount = int(raw)
        if amount <= 0:
            await msg.reply("❌ Сумма должна быть больше нуля. Введите другое значение.")
            return

        fund_id = _SELECTED_FUND.get(msg.user_id)
        if fund_id is None:
            msg.bot.storage.change_state(msg.user_id, VolunteerStates.MAIN_MENU)
            kb = volunteer_main_menu_keyboard()
            await msg.reply("⚠️ Фонд не выбран. Начните сначала через 'Лента фондов'.", keyboard=kb)
            return

        token = get_session_token(msg.user_id)
        if not token:
            msg.bot.storage.change_state(msg.user_id, VolunteerStates.MAIN_MENU)
            kb = volunteer_main_menu_keyboard()
            await msg.reply("⚠️ Нет активной сессии. /start", keyboard=kb)
            return

        donation = None
        try:
            donation = await backend_client.donate_to_fund(token, fund_id, amount)
        except Exception as e_donate:
            logger.warning("Donate failed user_id=%s fund_id=%s amount=%s error=%s", msg.user_id, fund_id, amount, e_donate)

        if not donation:
            kb_err = volunteer_main_menu_keyboard()
            await msg.reply(
                "❌ Не удалось выполнить донат. Попробуйте позже.",
                keyboard=kb_err,
            )
            return

        rating_earned = donation.get("rating_earned") or 0
        fund_status = donation.get("fund_status") or "—"
        fund_title = donation.get("fund_title") or f"ID {fund_id}"
        text = (
            "🙏 Спасибо за поддержку! Донат успешно выполнен.\n"
            "────────────────────\n"
            f"🧷 Фонд: {fund_title}\n"
            f"💸 Сумма: {amount}₽\n"
            f"⭐ Получено рейтинга: +{rating_earned}\n"
            f"📌 Статус фонда: {fund_status}\n"
            "────────────────────\n"
            "Вы можете вернуться к списку фондов или в главное меню."
        )
        msg.bot.storage.change_state(msg.user_id, VolunteerStates.MAIN_MENU)
        kb = donation_confirmation_keyboard()
        await msg.reply(text, keyboard=kb)

        _SELECTED_FUND.pop(msg.user_id, None)

    # --- возврат к ленте заявок ---
    @bot.on_button_callback(lambda d: d.payload == "back_to_feed")
    async def _back_to_feed(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        """Обработчик кнопки 'Назад к заявкам' / 'Вернуться к ленте' — возврат к ленте."""
        cb.bot.storage.change_state(cb.user_id, VolunteerStates.MAIN_MENU)
        await _send_events_feed(cb.user_id, lambda text, keyboard=None: cb.send(text, keyboard=keyboard))

    # --- возврат к главному меню волонтёра из ленты ---
    @bot.on_button_callback(lambda d: d.payload == "back_to_main_menu")
    async def _back_to_main_menu(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        """Обработчик кнопки 'Назад' из ленты — показывает главное меню волонтёра."""
        cb.bot.storage.change_state(cb.user_id, VolunteerStates.MAIN_MENU)
        kb = volunteer_main_menu_keyboard()
        await cb.send(
            "🤔 Чем хотите заняться?\n"
            "• Посмотреть ленту мероприятий\n"
            "• Посмотреть ленту фондов\n"
            "• Открыть профиль\n"
            "• Получить помощь\n\n"
            "Выберите действие кнопками ниже ⬇️",
            keyboard=kb
        )

    # --- возврат к ленте фондов ---
    @bot.on_button_callback(lambda d: d.payload == "back_to_funds")
    async def _back_to_funds(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        cb.bot.storage.change_state(cb.user_id, VolunteerStates.MAIN_MENU)
        await _send_funds_feed(cb.user_id, lambda text, keyboard=None: cb.send(text, keyboard=keyboard))

    # =========================
    # Профиль волонтёра (интерфейсный блок)
    # =========================
    @bot.on_button_callback(lambda d: d.payload == "profile")
    async def _profile_view(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        """Показ профиля пользователя.

        Концепция: интерфейс сначала. Пытаемся получить профиль + город.
        При ошибках/отсутствии данных показываем заглушки, чтобы UI работал стабильно.
        """
        # Состояние — остаёмся в MAIN_MENU для универсальных кнопок
        cb.bot.storage.change_state(cb.user_id, VolunteerStates.MAIN_MENU)
        await _render_profile(cb.user_id, lambda text, keyboard=None: cb.send(text, keyboard=keyboard))

    # --- мои отклики (волонтёр) ---
    @bot.on_button_callback(lambda d: d.payload == "my_applications")
    async def _my_applications(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        token = get_session_token(cb.user_id)
        kb_return = my_applications_return_keyboard()
        if not token:
            await cb.send("⚠️ Нет активной сессии. /start и повторите.", keyboard=kb_return)
            return
        resp = None
        try:
            resp = await backend_client.get_my_applications(token, page=1, page_size=10)
        except Exception as e_myapps:
            logger.warning("Get my applications failed user_id=%s error=%s", cb.user_id, e_myapps)
        applications = []
        if resp and isinstance(resp, dict):
            applications = resp.get("applications") or []
        if not applications:
            await cb.send("😕 У вас пока нет откликов.", keyboard=kb_return)
            return
        status_map = {
            "pending": "⏳ В ожидании",
            "approved": "✅ Принят",
            "rejected": "🚫 Отклонён",
            "participated": "🎉 Участвовал",
        }
        for app in applications:
            event_id = app.get("event_id")
            event_title = app.get("event_title") or "—"
            if len(event_title) > 60:
                event_title = event_title[:57] + "…"
            event_date = app.get("event_date") or "—"
            event_address = app.get("event_address") or "—"
            status_raw = app.get("status") or "unknown"
            status_local = status_map.get(status_raw, "❔ Неизвестный")
            rejection_reason = app.get("rejection_reason") or "—"
            applied_at = app.get("applied_at") or "—"
            reason_line = ""
            if status_raw == "rejected":
                reason_line = f"🚫 Причина: {rejection_reason}\n"
            text = (
                "📨 Мой отклик\n"
                "────────────────\n"
                f"🧷 ID события: {event_id}\n"
                f"📝 Название: {event_title}\n"
                f"🕒 Дата: {event_date}\n"
                f"📍 Адрес: {event_address}\n"
                f"📌 Статус: {status_local}\n"
                f"{reason_line}"
                f"🕒 Отклик: {applied_at}\n"
                "────────────────"
            )
            await cb.send(text)
        await cb.send("📑 Все отклики показаны.", keyboard=kb_return)

    # --- помощь (универсальная кнопка) ---
    @bot.on_button_callback(lambda d: d.payload == "help")
    async def _help_from_any(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        role = get_role(cb.user_id)
        # Волонтёр
        if role == "want_help":
            cb.bot.storage.change_state(cb.user_id, VolunteerStates.MAIN_MENU)
            kb = volunteer_main_menu_keyboard()
            await cb.send(
                "ℹ️ Помощь волонтёру\n"
                "────────────────\n"
                "• Лента заявок — мероприятия вашего города.\n"
                "• Отклик — нажмите 'Откликнуться' в карточке события.\n"
                "• Лента фондов — поддержите фонд и получите рейтинг.\n"
                "• Профиль — обновите город и интересы для релевантных событий.\n"
                "• Изменить город/интересы — кнопки в ленте.\n"
                "• Рейтинг растёт за участие и донаты.\n"
                "────────────────\n"
                "Если что-то пошло не так — /start перезапустит интерфейс.",
                keyboard=kb,
            )
            return
        # Админ / создатель фонда
        if role == "need_help":
            cb.bot.storage.change_state(cb.user_id, CommonStates.IDLE)
            kb = admin_help_keyboard()
            await cb.send(
                "ℹ️ Помощь администратора фонда\n"
                "────────────────\n"
                "• Создать событие — одна кнопка, отправьте 7 строк по формату.\n"
                "• Отклики — получите список ваших событий и затем ID для просмотра заявок.\n"
                "• Подтверждение участия — (будет добавлено) для начисления рейтинга волонтёрам.\n"
                "• Несколько фондов — выберите снова 'Нужна помощь' для регистрации ещё одного.\n"
                "• Город — если отсутствует, вводится при создании события.\n"
                "• Теги — точные теги повышают совпадение и интерес волонтёров.\n"
                "────────────────\n"
                "Выберите действие ниже или вернитесь назад.",
                keyboard=kb,
            )
            return
        # Нет роли
        kb = role_selection_keyboard()
        await cb.send(
            "⚠️ Роль не выбрана. Пожалуйста, выберите роль для продолжения.",
            keyboard=kb,
        )

    # --- админ заглушки ---
    @bot.on_button_callback(lambda d: d.payload == "admin_event_applications")
    async def _admin_event_applications(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        """Показ собственных мероприятий администратора и запрос ID для просмотра откликов."""
        token = get_session_token(cb.user_id)
        if not token:
            await cb.send("⚠️ Нет активной сессии. Используйте /start и повторите.")
            return
        events_resp = None
        try:
            events_resp = await backend_client.get_my_events(token, page=1, page_size=20)
        except Exception as e_my:
            logger.warning("Get my events failed user_id=%s error=%s", cb.user_id, e_my)
        events = []
        if events_resp:
            # поддержка формата {"events": [...]} либо прямого списка
            if isinstance(events_resp, dict):
                events = events_resp.get("events") or []
            elif isinstance(events_resp, list):
                events = events_resp
        if not events:
            kb_back = admin_fund_main_keyboard()
            await cb.send("😕 У вас пока нет созданных мероприятий.", keyboard=kb_back)
            return
        # словарь отображения тегов по ID/строке
        tag_map = {"1": "экология", "2": "образование", "3": "медицина", "4": "дети", "5": "животные"}
        for ev in events:
            eid = ev.get("id")
            title = ev.get("title") or "—"
            description = ev.get("description") or "—"
            address = ev.get("address") or "—"
            contact = ev.get("contact") or "—"
            what_to_do = ev.get("what_to_do") or "—"
            date = ev.get("date") or "—"
            raw_tags = ev.get("tags") or []
            # преобразуем теги: если элементы выглядят как числа 1..5 -> русские названия, иначе исходные
            tag_tokens: list[str] = []
            for t in raw_tags:
                t_str = str(t).strip()
                tag_tokens.append(tag_map.get(t_str, t_str))
            tags_joined = ",".join(tag_tokens) if tag_tokens else "—"
            creator = ev.get("creator_username") or "—"
            created_at = ev.get("created_at") or "—"
            city_id = ev.get("city_id")
            created_by = ev.get("created_by")
            text = (
                "📌 Ваше мероприятие\n"
                "────────────────\n"
                f"🧷 ID: {eid}\n"
                f"📝 Название: {title}\n"
                f"📄 Описание: {description}\n"
                f"📍 Адрес: {address}\n"
                f"☎️ Контакт: {contact}\n"
                f"🛠️ Что делать: {what_to_do}\n"
                f"🕒 Дата: {date}\n"
                f"🏙️ City_ID: {city_id}\n"
                f"👤 Создатель (ID): {created_by}\n"
                f"👤 Логин создателя: {creator}\n"
                f"📆 Создано: {created_at}\n"
                f"🏷️ Теги: {tags_joined}\n"
                "────────────────\n"
                "Чтобы увидеть отклики — отправьте его ID одним сообщением." 
            )
            await cb.send(text)
        cb.bot.storage.change_state(cb.user_id, AdminStates.WAIT_EVENT_APPS_EVENT_ID)
        await cb.send("✉️ Введите ID мероприятия, отклики которого хотите посмотреть (число).")

    # --- ввод ID мероприятия для показа откликов ---
    @bot.on_message(is_state(AdminStates.WAIT_EVENT_APPS_EVENT_ID))
    async def _admin_event_apps_id(msg: aiomax.Message, cursor: aiomax.FSMCursor):
        raw = (getattr(msg, "text", None) or getattr(msg, "content", "") or "").strip()
        if not raw:
            await msg.reply("⚠️ Пусто. Введите числовой ID мероприятия.")
            return
        if not raw.isdigit():
            await msg.reply("❌ Нужно число. Попробуйте ещё раз.")
            return
        event_id = int(raw)
        token = get_session_token(msg.user_id)
        if not token:
            await msg.reply("⚠️ Нет активной сессии. /start и повторите.")
            return
        apps_resp = None
        try:
            apps_resp = await backend_client.get_event_applications(token, event_id, page=1, page_size=50)
        except Exception as e_apps:
            logger.warning("Get event applications failed user_id=%s event_id=%s error=%s", msg.user_id, event_id, e_apps)
        applications: list[dict] = []
        if apps_resp:
            if isinstance(apps_resp, dict):
                # ожидаемый ключ
                if "applications" in apps_resp and isinstance(apps_resp.get("applications"), list):
                    applications = apps_resp.get("applications")
                else:
                    # если структура одиночная — обёрнем
                    # проверим наличие user_id и event_id как признаки отдельного отклика
                    if "user_id" in apps_resp and "event_id" in apps_resp:
                        applications = [apps_resp]
            elif isinstance(apps_resp, list):
                applications = apps_resp
        kb_back = admin_fund_main_keyboard()
        if not applications:
            msg.bot.storage.change_state(msg.user_id, CommonStates.IDLE)
            await msg.reply("😕 Откликов на это мероприятие пока нет.", keyboard=kb_back)
            return
        # Отобразим каждый отклик
        for app in applications:
            app_id = app.get("id")
            status = app.get("status") or "—"
            rejection_reason = app.get("rejection_reason") or "—"
            user_id = app.get("user_id")
            applied_at = app.get("applied_at") or "—"
            username = app.get("user_username") or "—"
            user_rating = app.get("user_rating") or 0
            participation_count = app.get("user_participation_count") or 0
            user_city_id = app.get("user_city_id")
            about_me = app.get("user_about_me") or "—"
            interests = app.get("user_interests") or []
            interests_joined = ", ".join(interests) if interests else "—"
            match_pct = app.get("match_percentage") or 0
            text = (
                "📨 Отклик волонтёра\n"
                "────────────────\n"
                f"🧷 ID отклика: {app_id}\n"
                f"🧷 ID события: {event_id}\n"
                f"📌 Статус: {status}\n"
                f"🚫 Причина отказа: {rejection_reason}\n"
                f"👤 Волонтёр ID: {user_id}\n"
                f"👤 Логин: {username}\n"
                f"⭐ Рейтинг: {user_rating}\n"
                f"✅ Участий: {participation_count}\n"
                f"🏙️ Город ID: {user_city_id}\n"
                f"🗣️ О себе: {about_me}\n"
                f"🎯 Интересы: {interests_joined}\n"
                f"🔍 Совпадение: {match_pct}%\n"
                f"🕒 Дата отклика: {applied_at}\n"
                "────────────────"
            )
            if status == "pending":
                kb_mod = application_moderation_keyboard(app_id)
                await msg.reply(text + "\nВыберите действие:", keyboard=kb_mod)
            else:
                await msg.reply(text)
        msg.bot.storage.change_state(msg.user_id, CommonStates.IDLE)
        await msg.reply("📑 Все отклики показаны. Вы можете вернуться в меню.", keyboard=kb_back)

    # ===== Модерация отклика: принять =====
    @bot.on_button_callback(lambda d: d.payload.startswith("app_approve_"))
    async def _application_approve(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        token = get_session_token(cb.user_id)
        if not token:
            await cb.send("⚠️ Нет активной сессии. /start и повторите.")
            return
        try:
            app_id_str = cb.payload.replace("app_approve_", "")
            if not app_id_str.isdigit():
                await cb.send("❌ Некорректный ID отклика.")
                return
            app_id = int(app_id_str)
        except Exception:
            await cb.send("❌ Ошибка разбора ID отклика.")
            return
        updated = None
        try:
            updated = await backend_client.update_application(token, app_id, status="approved")
        except Exception as e_up:
            logger.warning("Approve application failed user_id=%s app_id=%s error=%s", cb.user_id, app_id, e_up)
        kb = admin_fund_main_keyboard()
        if not updated:
            await cb.send("❌ Не удалось подтвердить отклик. Попробуйте позже.", keyboard=kb)
            return
        await cb.send(
            "✅ Отклик подтверждён! Волонтёр может участвовать. Возврат в меню:",
            keyboard=kb,
        )

    # ===== Модерация отклика: инициировать отказ =====
    _PENDING_REJECTION_APP: dict[int, int] = {}

    @bot.on_button_callback(lambda d: d.payload.startswith("app_reject_"))
    async def _application_reject_init(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        token = get_session_token(cb.user_id)
        if not token:
            await cb.send("⚠️ Нет активной сессии. /start и повторите.")
            return
        app_id_str = cb.payload.replace("app_reject_", "")
        if not app_id_str.isdigit():
            await cb.send("❌ Некорректный ID отклика.")
            return
        app_id = int(app_id_str)
        _PENDING_REJECTION_APP[cb.user_id] = app_id
        cb.bot.storage.change_state(cb.user_id, AdminStates.WAIT_APPLICATION_REJECTION_REASON)
        await cb.send(
            "✏️ Введите причину отказа одним сообщением (кратко). Например: недостаточно опыта."
        )

    # ===== Модерация отклика: ввод причины отказа =====
    @bot.on_message(is_state(AdminStates.WAIT_APPLICATION_REJECTION_REASON))
    async def _application_reject_reason(msg: aiomax.Message, cursor: aiomax.FSMCursor):
        reason_raw = (getattr(msg, "text", None) or getattr(msg, "content", "") or "").strip()
        if not reason_raw:
            await msg.reply("⚠️ Пусто. Введите причину отказа.")
            return
        app_id = _PENDING_REJECTION_APP.get(msg.user_id)
        if app_id is None:
            msg.bot.storage.change_state(msg.user_id, CommonStates.IDLE)
            kb = admin_fund_main_keyboard()
            await msg.reply("⚠️ ID отклика потерян. Начните заново через просмотр откликов.", keyboard=kb)
            return
        token = get_session_token(msg.user_id)
        if not token:
            kb = admin_fund_main_keyboard()
            await msg.reply("⚠️ Нет активной сессии. /start и повторите.", keyboard=kb)
            return
        updated = None
        try:
            updated = await backend_client.update_application(token, app_id, status="rejected", rejection_reason=reason_raw)
        except Exception as e_up:
            logger.warning("Reject application failed user_id=%s app_id=%s error=%s", msg.user_id, app_id, e_up)
        kb = admin_fund_main_keyboard()
        if not updated:
            msg.bot.storage.change_state(msg.user_id, CommonStates.IDLE)
            await msg.reply("❌ Не удалось отклонить отклик. Попробуйте позже.", keyboard=kb)
            return
        _PENDING_REJECTION_APP.pop(msg.user_id, None)
        msg.bot.storage.change_state(msg.user_id, CommonStates.IDLE)
        await msg.reply(
            "🚫 Отклик отклонён. Причина сохранена. Возврат в меню:",
            keyboard=kb,
        )

    @bot.on_button_callback(lambda d: d.payload == "admin_create_event")
    async def _admin_create_event(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        cb.bot.storage.change_state(cb.user_id, AdminStates.WAIT_EVENT_INFO)
        await cb.send(
            "🛠️ Создание мероприятия. Отправьте ОДНО сообщение с данными:\n"
            "Название\nОписание\nАдрес\nКонтакт (телефон/email)\nЧто_нужно_делать\nДата (YYYY-MM-DD или ISO 8601)\nТеги (например: 1,2,4)\n\n"
            "Теги: 1-экология 2-образование 3-медицина 4-дети 5-животные\n"
            "Пример:\nПомощь детям\nНужна помощь детям в учебе\nул. Ленина, д. 16\n+79991234567\nОбъяснять математику и русский язык\n2024-01-15T10:00:00Z\n2,4"
        )

    # --- ввод данных мероприятия ---
    @bot.on_message(is_state(AdminStates.WAIT_EVENT_INFO))
    async def _admin_event_info(msg: aiomax.Message, cursor: aiomax.FSMCursor):
        raw = (getattr(msg, "text", None) or getattr(msg, "content", "") or "").strip()
        if not raw:
            await msg.reply("⚠️ Пусто. Отправьте данные одним сообщением по ранее указанному формату.")
            return
        parts = [p.strip() for p in raw.replace(";", "\n").split("\n") if p.strip()]
        if len(parts) < 7:
            await msg.reply("❌ Недостаточно строк. Нужно 7: Название, Описание, Адрес, Контакт, Что_нужно_делать, Дата, Теги.")
            return
        title, description, address, contact, what_to_do, date_raw, tags_raw = parts[:7]

        # Дата: допускаем YYYY-MM-DD -> преобразуем в ISO с фиксированным временем 10:00:00Z
        from datetime import datetime
        date_iso = None
        if date_raw.lower() == "-":
            await msg.reply("❌ Дата обязательна. Укажите дату (YYYY-MM-DD или полный ISO).")
            return
        try:
            if len(date_raw) == 10 and date_raw.count("-") == 2:
                # YYYY-MM-DD
                dt = datetime.fromisoformat(date_raw)
                date_iso = dt.replace(hour=10, minute=0, second=0, microsecond=0).isoformat() + "Z"
            else:
                # Попытка напрямую
                dt = datetime.fromisoformat(date_raw.replace("Z", ""))
                date_iso = (dt.isoformat() + "Z") if not date_raw.endswith("Z") else date_raw
        except Exception:
            await msg.reply("❌ Некорректная дата. Используйте YYYY-MM-DD или ISO 8601 (2024-01-15T10:00:00Z).")
            return

        allowed_tag_ids = {1,2,3,4,5}
        tag_ids: list[int] = []
        for tok in tags_raw.split(","):
            tok = tok.strip()
            if not tok:
                continue
            if not tok.isdigit():
                await msg.reply("❌ Теги должны быть числами, например: 1,2,5")
                return
            val = int(tok)
            if val not in allowed_tag_ids:
                await msg.reply("❌ Недопустимый тег. Разрешены: 1,2,3,4,5")
                return
            tag_ids.append(val)
        if not tag_ids:
            await msg.reply("❌ Нужен хотя бы один тег.")
            return

        token = get_session_token(msg.user_id)
        if not token:
            await msg.reply("⚠️ Нет активной сессии. /start и повторите.")
            return

        # Получаем city_id из профиля
        city_id = None
        try:
            profile = await backend_client.get_user_profile(token)
            city_id = profile.get("city_id")
        except Exception as e_prof:
            logger.warning("Profile fetch for event create failed user_id=%s error=%s", msg.user_id, e_prof)
        if city_id is None:
            # Сохраняем распарсенные данные и просим ввести город прямо сейчас
            _PENDING_EVENT_DATA[msg.user_id] = {
                "title": title,
                "description": description,
                "address": address,
                "contact": contact,
                "what_to_do": what_to_do,
                "date_iso": date_iso,
                "tag_ids": tag_ids,
            }
            msg.bot.storage.change_state(msg.user_id, AdminStates.WAIT_EVENT_CITY)
            await msg.reply(
                f"🏙️ У вашего профиля не указан город. Введите название города одним сообщением.\n{CITY_PROMPT_SUFFIX}\nНапример: Москва"
            )
            return

        payload = {
            "title": title,
            "description": description,
            "address": address,
            "contact": contact,
            "what_to_do": what_to_do,
            "date": date_iso,
            "city_id": city_id,
            "tag_ids": tag_ids,
        }
        created = None
        try:
            created = await backend_client.create_event(token, payload)
        except Exception as e_ce:
            logger.warning("Create event failed user_id=%s error=%s", msg.user_id, e_ce)
        if not created:
            await msg.reply("❌ Не удалось создать мероприятие. Проверьте формат и повторите позже.")
            return
        msg.bot.storage.change_state(msg.user_id, CommonStates.IDLE)
        kb_done = admin_event_created_keyboard()
        await msg.reply(
            "🎉 Мероприятие создано!\n"
            f"🧷 ID: {created.get('id')}\n"
            f"📝 Название: {created.get('title')}\n"
            f"📍 Адрес: {created.get('address')}\n"
            f"🕒 Дата: {created.get('date')}\n"
            "Спасибо за создание. Возврат в меню:",
            keyboard=kb_done,
        )

    # --- ввод города в процессе создания события ---
    @bot.on_message(is_state(AdminStates.WAIT_EVENT_CITY))
    async def _admin_event_city(msg: aiomax.Message, cursor: aiomax.FSMCursor):
        raw_city = (getattr(msg, "text", None) or getattr(msg, "content", "") or "").strip()
        if not raw_city:
            await msg.reply(f"⚠️ Пусто. Введите название города.\n{CITY_PROMPT_SUFFIX}")
            return
        token = get_session_token(msg.user_id)
        if not token:
            await msg.reply("⚠️ Нет активной сессии. /start и повторите.")
            return
        matched_city = None
        try:
            cities = await backend_client.get_cities(page=1, page_size=MAX_CITIES_PAGE_SIZE)
            lowered = raw_city.lower()
            for c in cities:
                name = (c.get("name") or "").strip()
                if name.lower() == lowered:
                    matched_city = c
                    break
        except Exception as e_cities:
            logger.warning("Admin event city: fetch cities failed user_id=%s error=%s", msg.user_id, e_cities)
        if not matched_city:
            await msg.reply(f"❌ Город не найден. Допустимые: {CITY_PROMPT_SUFFIX}")
            return
        city_id = matched_city.get("id")
        city_name = matched_city.get("name") or raw_city
        saved_ok = True
        try:
            # ensure profile exists then patch
            try:
                await backend_client.get_user_profile(token)
            except Exception as e_prof_init:
                logger.warning("Admin event city: profile init failed user_id=%s error=%s", msg.user_id, e_prof_init)
            res_profile = await backend_client.update_user_profile_city(token, city_id)
            if res_profile is None:
                saved_ok = False
        except Exception as e_save_city:
            logger.warning("Admin event city: update failed user_id=%s city_id=%s error=%s", msg.user_id, city_id, e_save_city)
            saved_ok = False
        if not saved_ok:
            await msg.reply("❌ Не удалось сохранить город. Попробуйте снова или позже.")
            return
        data = _PENDING_EVENT_DATA.pop(msg.user_id, None)
        if not data:
            msg.bot.storage.change_state(msg.user_id, VolunteerStates.MAIN_MENU)
            await msg.reply("⚠️ Данные мероприятия потеряны. Начните создание снова через 'Создать новое событие'.")
            return
        payload = {
            "title": data["title"],
            "description": data["description"],
            "address": data["address"],
            "contact": data["contact"],
            "what_to_do": data["what_to_do"],
            "date": data["date_iso"],
            "city_id": city_id,
            "tag_ids": data["tag_ids"],
        }
        created = None
        try:
            created = await backend_client.create_event(token, payload)
        except Exception as e_ce_final:
            logger.warning("Create event (after city) failed user_id=%s error=%s", msg.user_id, e_ce_final)
        if not created:
            msg.bot.storage.change_state(msg.user_id, VolunteerStates.MAIN_MENU)
            await msg.reply("❌ Не удалось создать мероприятие после сохранения города. Попробуйте снова.")
            return
        msg.bot.storage.change_state(msg.user_id, CommonStates.IDLE)
        kb_done = admin_event_created_keyboard()
        await msg.reply(
            "🎉 Мероприятие создано!\n"
            f"🏙️ Город: {city_name}\n"
            f"🧷 ID: {created.get('id')}\n"
            f"📝 Название: {created.get('title')}\n"
            f"📍 Адрес: {created.get('address')}\n"
            f"🕒 Дата: {created.get('date')}\n"
            "Спасибо за создание. Возврат в меню:",
            keyboard=kb_done,
        )

    # --- возврат в главное админское меню ---
    @bot.on_button_callback(lambda d: d.payload == "admin_back_to_main")
    async def _admin_back_to_main(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        kb = admin_fund_main_keyboard()
        await cb.send("🏠 Главное меню администратора фондов:", keyboard=kb)

    # --- редактирование профиля ---
    @bot.on_button_callback(lambda d: d.payload == "edit_profile")
    async def _edit_profile(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        # Используем существующую логику: сначала город, затем интересы
        _set_return_to_profile(cb.user_id)
        cb.bot.storage.change_state(cb.user_id, VolunteerStates.WAIT_CITY)
        await cb.send(
            f"📝 Обновление города. Напишите новый город одним сообщением.\n{CITY_PROMPT_SUFFIX}"
        )

    # --- изменение города из ленты ---
    @bot.on_button_callback(lambda d: d.payload == "change_city")
    async def _feed_change_city(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        _set_return_to_feed(cb.user_id)
        cb.bot.storage.change_state(cb.user_id, VolunteerStates.WAIT_CITY)
        await cb.send(
            f"🏙️ Укажите город (одно сообщение).\n{CITY_PROMPT_SUFFIX}\n"
            "Например: Санкт-Петербург"
        )

    # --- изменение фильтров/интересов из ленты ---
    @bot.on_button_callback(lambda d: d.payload == "change_filters")
    async def _feed_change_filters(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        _set_return_to_feed(cb.user_id)
        cb.bot.storage.change_state(cb.user_id, VolunteerStates.WAIT_INTERESTS)
        await cb.send(
            f"🎯 Укажите ваши интересы (одно сообщение, через запятую).\n{INTERESTS_PROMPT_SUFFIX}\n"
            "Например: экология, дети"
        )

    # --- ветка «Нужна помощь»: ввод данных фонда ---
    @bot.on_message(is_state(HelpRequestStates.WAIT_FUND_INFO))
    async def _fund_info(msg: aiomax.Message, cursor: aiomax.FSMCursor):
        raw = (getattr(msg, "text", None) or getattr(msg, "content", "") or "").strip()
        if not raw:
            await msg.reply("⚠️ Пусто. Отправьте данные фонда одним сообщением.")
            return
        parts = [p.strip() for p in raw.replace(";", "\n").split("\n") if p.strip()]
        if len(parts) < 7:
            await msg.reply("❌ Недостаточно строк. Нужно 7: Название, Описание, Реквизиты, Целевая_сумма, Рейтинг_за_100, Дата, Теги.")
            return
        title, description, requisites, target_raw, rating_raw, end_date_raw, tags_raw = parts[:7]
        # Санитизация числовых значений: удаляем пробелы, нецифровые разделители (на случай '100 000' или '100 000')
        def _clean_number(s: str) -> str:
            return "".join(ch for ch in s if ch.isdigit())
        original_target = target_raw
        original_rating = rating_raw
        target_raw = _clean_number(target_raw)
        rating_raw = _clean_number(rating_raw)
        if not target_raw:
            await msg.reply("❌ Целевая_сумма пуста или не содержит цифр. Укажите положительное число без букв.")
            return
        try:
            target_amount = int(target_raw)
            if target_amount <= 0:
                raise ValueError
        except Exception as e_target:
            logger.warning("Fund create: invalid target_amount raw='%s' cleaned='%s' user_id=%s error=%s", original_target, target_raw, msg.user_id, e_target)
            await msg.reply("❌ Целевая_сумма должна быть положительным целым числом. Пример: 100000")
            return
        if not rating_raw:
            await msg.reply("❌ Рейтинг_за_100 пуст или не содержит цифр. Пример: 1")
            return
        try:
            rating_per_100 = int(rating_raw)
            if rating_per_100 <= 0:
                raise ValueError
        except Exception as e_rating:
            logger.warning("Fund create: invalid rating_per_100 raw='%s' cleaned='%s' user_id=%s error=%s", original_rating, rating_raw, msg.user_id, e_rating)
            await msg.reply("❌ Рейтинг_за_100 должен быть положительным целым числом. Пример: 1")
            return
        end_date = None
        if end_date_raw.strip() != "-":
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(end_date_raw.strip())
                end_date = dt.isoformat()
            except Exception:
                await msg.reply("❌ Некорректная дата. Формат YYYY-MM-DD или '-' для бессрочно.")
                return
        allowed_tag_ids = {1,2,3,4,5}
        tag_ids: list[int] = []
        for tok in tags_raw.split(","):
            tok = tok.strip()
            if not tok:
                continue
            if not tok.isdigit():
                await msg.reply("❌ Теги должны быть числами, например: 1,2,5")
                return
            val = int(tok)
            if val not in allowed_tag_ids:
                await msg.reply("❌ Недопустимый тег. Разрешены: 1,2,3,4,5")
                return
            tag_ids.append(val)
        if not tag_ids:
            await msg.reply("❌ Нужно указать хотя бы один тег.")
            return
        token = get_session_token(msg.user_id)
        if not token:
            await msg.reply("⚠️ Нет активной сессии. /start и повторите.")
            return
        payload = {
            "title": title,
            "description": description,
            "requisites": requisites,
            "target_amount": target_amount,
            "rating_per_100": rating_per_100,
            "end_date": end_date,
            "tag_ids": tag_ids,
        }
        created = None
        try:
            created = await backend_client.create_fund(token, payload)
        except Exception as e_cf:
            logger.warning("Create fund failed user_id=%s error=%s", msg.user_id, e_cf)
        if not created:
            await msg.reply("❌ Не удалось создать фонд. Проверьте формат и повторите позже.")
            return
        msg.bot.storage.change_state(msg.user_id, CommonStates.IDLE)
        kb_admin = admin_fund_main_keyboard()
        await msg.reply(
            "🎉 Фонд зарегистрирован! Спасибо за регистрацию.\n"
            f"🧷 ID: {created.get('id')}\n"
            f"📝 Название: {created.get('title')}\n"
            f"🎯 Цель: {created.get('target_amount')}₽\n"
            f"📦 Собрано: {created.get('collected_amount', 0)}₽\n"
            "Главное меню фондов:",
            keyboard=kb_admin,
        )

    # --- ветка «Хочу помочь»: город ---
    @bot.on_message(is_state(VolunteerStates.WAIT_CITY))
    async def _volunteer_city(msg: aiomax.Message, cursor: aiomax.FSMCursor):
        user_input_raw = (getattr(msg, "text", None) or getattr(msg, "content", "") or "").strip()
        if not user_input_raw:
            await msg.reply(
                f"⚠️ Пусто. Напишите название города.\n{CITY_PROMPT_SUFFIX}"
            )
            return

        token = get_session_token(msg.user_id)
        if not token:
            # Нет токена — интерфейсная деградация: просим повторить позже
            await msg.reply(
                "⚠️ Сервис временно недоступен. Попробуйте /start чуть позже."
            )
            return

        # Получаем список городов для сопоставления (интерфейс сначала — ошибки не ломают UX)
        matched_city = None
        try:
            # Используем допустимый page_size. При необходимости можно сделать пагинацию.
            cities = await backend_client.get_cities(page=1, page_size=MAX_CITIES_PAGE_SIZE)
            lowered = user_input_raw.lower()
            for c in cities:
                name = (c.get("name") or "").strip()
                if name.lower() == lowered:
                    matched_city = c
                    break
        except Exception as e_cities:
            logger.warning("Fetch cities failed user_id=%s error=%s", msg.user_id, e_cities)

        if not matched_city:
            await msg.reply(
                f"❌ Город не найден. Введите один из: {CITY_PROMPT_SUFFIX}"
            )
            return  # остаёмся в WAIT_CITY

        city_id = matched_city.get("id")
        city_name = matched_city.get("name") or user_input_raw

        saved_ok = True
        try:
            # Вариант B: гарантируем существование профиля перед PATCH.
            try:
                await backend_client.get_user_profile(token)
            except Exception as e_profile_init:
                logger.warning("Profile init (pre-city-patch) failed user_id=%s error=%s", msg.user_id, e_profile_init)
            profile_after = await backend_client.update_user_profile_city(token, city_id)
            if profile_after is None:
                saved_ok = False
        except Exception as e_save:
            logger.warning("Update city failed user_id=%s city_id=%s error=%s", msg.user_id, city_id, e_save)
            saved_ok = False

        if not saved_ok:
            await msg.reply(
                "❌ Не удалось сохранить город. Попробуйте позже или повторите ввод."
            )
            return

        # Если возврат к ленте
        if _pop_return_to_feed(msg.user_id):
            msg.bot.storage.change_state(msg.user_id, VolunteerStates.MAIN_MENU)
            await msg.reply(f"✅ Город обновлён: {city_name}")
            await _send_events_feed(msg.user_id, lambda text, keyboard=None: msg.reply(text, keyboard=keyboard))
            return

        # Профиль редактируется — переходим к интересам
        if _has_return_to_profile(msg.user_id):
            msg.bot.storage.change_state(msg.user_id, VolunteerStates.WAIT_INTERESTS)
            await msg.reply(
                f"✅ Город обновлён: {city_name}\n\n"
                f"Теперь укажите новые интересы (одно сообщение).\n{INTERESTS_PROMPT_SUFFIX}"
            )
            return

        # Регистрация — переходим к интересам
        msg.bot.storage.change_state(msg.user_id, VolunteerStates.WAIT_INTERESTS)
        await msg.reply(
            f"✅ Город получен: {city_name}\n\n"
            f"Теперь укажите интересы (одно сообщение, через запятую).\n{INTERESTS_PROMPT_SUFFIX}"
        )

    # --- ветка «Хочу помочь»: интересы 
    @bot.on_message(is_state(VolunteerStates.WAIT_INTERESTS))
    async def _volunteer_interests(msg: aiomax.Message, cursor: aiomax.FSMCursor):
        raw_input = (getattr(msg, "text", None) or getattr(msg, "content", "") or "").strip()
        if not raw_input:
            await msg.reply(
                f"⚠️ Пусто. Напишите ваши интересы через запятую.\n{INTERESTS_PROMPT_SUFFIX}"
            )
            return

        token = get_session_token(msg.user_id)
        if not token:
            await msg.reply(
                "⚠️ Сервис временно недоступен. Попробуйте /start чуть позже."
            )
            return

        # Парсим ввод: поддержим разделение запятыми или новой строкой.
        parts = [p.strip() for p in raw_input.replace("\n", ",").split(",") if p.strip()]
        lowered_set = {p.lower() for p in parts}

        matched_tag_ids: list[int] = []
        matched_names: list[str] = []
        try:
            tags = await backend_client.get_tags(page=1, page_size=100)
            # Строим индекс по названию (lower) -> id
            for t in tags:
                name = (t.get("name") or "").strip()
                if not name:
                    continue
                if name.lower() in lowered_set:
                    matched_tag_ids.append(t.get("id"))
                    matched_names.append(name)
        except Exception as e_tags:
            logger.warning("Fetch tags failed user_id=%s error=%s", msg.user_id, e_tags)

        if not matched_tag_ids:
            await msg.reply(
                f"❌ Ни один интерес не совпал. Используйте варианты: {INTERESTS_PROMPT_SUFFIX}"
            )
            return  # остаёмся в WAIT_INTERESTS

        # Optionally ensure profile exists like with city update
        try:
            await backend_client.get_user_profile(token)
        except Exception as e_profile_init:
            logger.warning("Profile init (pre-interests) failed user_id=%s error=%s", msg.user_id, e_profile_init)

        saved_ok = True
        try:
            res = await backend_client.update_user_interests(token, matched_tag_ids)
            if res is None:
                saved_ok = False
        except Exception as e_save:
            logger.warning("Update interests failed user_id=%s tags=%s error=%s", msg.user_id, matched_tag_ids, e_save)
            saved_ok = False

        if not saved_ok:
            await msg.reply(
                "❌ Не удалось сохранить интересы. Повторите попытку позже."
            )
            return

        joined_names = ", ".join(matched_names)

        if _pop_return_to_feed(msg.user_id):
            msg.bot.storage.change_state(msg.user_id, VolunteerStates.MAIN_MENU)
            await msg.reply(f"✅ Интересы обновлены: {joined_names}")
            await _send_events_feed(msg.user_id, lambda text, keyboard=None: msg.reply(text, keyboard=keyboard))
            return

        # Завершение редактирования профиля
        if _has_return_to_profile(msg.user_id):
            _clear_return_to_profile(msg.user_id)
            msg.bot.storage.change_state(msg.user_id, VolunteerStates.MAIN_MENU)
            await msg.reply(f"✅ Интересы обновлены: {joined_names}")
            # Показ свежего профиля
            await _render_profile(msg.user_id, lambda text, keyboard=None: msg.reply(text, keyboard=keyboard))
            return

        msg.bot.storage.change_state(msg.user_id, VolunteerStates.MAIN_MENU)
        kb = volunteer_main_menu_keyboard()
        await msg.reply(
            f"🎯 Интересы сохранены: {joined_names}\n\n"
            "Выберите следующее действие ниже ⬇️",
            keyboard=kb,
        )


# =========================
# Внутреннее: стартовое сообщение
# =========================

async def _send_welcome(
    user_id: int,
    send_callable: Callable[[str, Any | None], Awaitable[aiomax.Message]],
) -> None:
    """Единое место отправки стартового сообщения (и клавиатуры)."""
    # Проверка: не отправлять повторно для не-тестовых с выбранной ролью
    if user_id != TEST_USER_ID and get_role(user_id):
        return
    
    kb = role_selection_keyboard()
    await send_callable(WELCOME_MESSAGE, keyboard=kb)
