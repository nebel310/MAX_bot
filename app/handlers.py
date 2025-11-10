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
from typing import Callable, Awaitable, Any

import aiomax

from app.keyboards.inline_keyboards import (
    role_selection_keyboard,
    volunteer_main_menu_keyboard,
    feed_actions_keyboard,
    request_details_keyboard,
    response_confirmation_keyboard,
)
from app.states import VolunteerStates, HelpRequestStates, CommonStates
from app.services.role_stub import get_role, set_role, MOCK_FEED_MESSAGE, MOCK_REQUEST_DETAILS


# =========================
# Конфигурация/константы
# =========================

WELCOME_MESSAGE = (
    "Привет! Это демо интерфейса бота.\n\n"
    "Выберите роль, чтобы протестировать кнопки и переходы."
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

def _set_return_to_feed(user_id: int) -> None:
    _RETURN_TO_FEED[user_id] = True

def _pop_return_to_feed(user_id: int) -> bool:
    """Вернёт True, если был запрошен возврат к ленте, и сразу сбросит флаг."""
    return _RETURN_TO_FEED.pop(user_id, False)

async def _show_feed(send_callable: Callable[[str, Any | None], Awaitable[aiomax.Message]]) -> None:
    """Показ ленты с клавиатурой действий."""
    kb = feed_actions_keyboard()
    await send_callable(MOCK_FEED_MESSAGE, keyboard=kb)


# =========================
# Регистрация хендлеров
# =========================

def setup_handlers(bot: aiomax.Bot) -> None:

    # --- старт через текст "start" (для тестов) ---
    @bot.on_message("start")
    async def _start_message(msg: aiomax.Message, cursor: aiomax.FSMCursor):
        await _send_welcome(
            user_id=msg.user_id,
            send_callable=lambda text, keyboard=None: msg.reply(text, keyboard=keyboard),
        )
        msg.bot.storage.change_state(msg.user_id, CommonStates.IDLE)

    # --- платформенный старт (кнопка "Начать" в ЛС) ---
    @bot.on_bot_start()
    async def _on_start(payload: aiomax.BotStartPayload, cursor: aiomax.FSMCursor):
        await _send_welcome(
            user_id=payload.user_id,
            send_callable=lambda text, keyboard=None: payload.send(text, keyboard=keyboard),
        )
        payload.bot.storage.change_state(payload.user_id, CommonStates.IDLE)

    # --- выбор роли: нужна помощь ---
    @bot.on_button_callback(lambda d: d.payload == "need_help")
    async def _need_help(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        if not _can_change_role(cb.user_id):
            return
        set_role(cb.user_id, "need_help")
        cb.bot.storage.change_state(cb.user_id, HelpRequestStates.WAIT_DESCRIPTION)
        await cb.send("Опишите кратко, какая нужна помощь (одно сообщение).")

    # --- выбор роли: хочу помочь ---
    @bot.on_button_callback(lambda d: d.payload == "want_help")
    async def _want_help(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        if not _can_change_role(cb.user_id):
            return
        set_role(cb.user_id, "want_help")
        cb.bot.storage.change_state(cb.user_id, VolunteerStates.WAIT_CITY)
        await cb.send("Укажите город (одно сообщение).")

    # --- лента заявок ---
    @bot.on_button_callback(lambda d: d.payload == "feed")
    async def _feed(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        """Обработчик кнопки 'Лента заявок' — показываем mock-данные с клавиатурой действий."""
        await _show_feed(lambda text, keyboard=None: cb.send(text, keyboard=keyboard))

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
        """Обработчик кнопки 'Откликнуться' — отправка отклика волонтёра."""
        # TODO: backend.send_response(user_id=cb.user_id, request_id=1)
        kb = response_confirmation_keyboard()
        await cb.send(
            'Ваш отклик отправлен фонду "ЭкоМир"!\nС вами свяжутся в течение 24 часов.',
            keyboard=kb
        )

    # --- возврат к ленте заявок ---
    @bot.on_button_callback(lambda d: d.payload == "back_to_feed")
    async def _back_to_feed(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        """Обработчик кнопки 'Назад к заявкам' / 'Вернуться к ленте' — возврат к ленте."""
        await _show_feed(lambda text, keyboard=None: cb.send(text, keyboard=keyboard))

    # --- изменение города из ленты ---
    @bot.on_button_callback(lambda d: d.payload == "change_city")
    async def _feed_change_city(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        _set_return_to_feed(cb.user_id)
        cb.bot.storage.change_state(cb.user_id, VolunteerStates.WAIT_CITY)
        await cb.send("Укажите город (одно сообщение).")

    # --- изменение фильтров/интересов из ленты ---
    @bot.on_button_callback(lambda d: d.payload == "change_filters")
    async def _feed_change_filters(cb: aiomax.Callback, cursor: aiomax.FSMCursor):
        _set_return_to_feed(cb.user_id)
        cb.bot.storage.change_state(cb.user_id, VolunteerStates.WAIT_INTERESTS)
        await cb.send("Теперь укажите ваши интересы (чем готовы помочь) одним сообщением.")

    # --- ветка «Нужна помощь»: описание запроса ---
    @bot.on_message(is_state(HelpRequestStates.WAIT_DESCRIPTION))
    async def _help_description(msg: aiomax.Message, cursor: aiomax.FSMCursor):
        text = (getattr(msg, "text", None) or getattr(msg, "content", "") or "").strip()
        if not text:
            await msg.reply("Пусто. Опишите, какая нужна помощь.")
            return
        # TODO: backend.save_help_request(msg.user_id, text)
        msg.bot.storage.change_state(msg.user_id, CommonStates.IDLE)
        await msg.reply("Спасибо! Ваша заявка сохранена (демо).")

    # --- ветка «Хочу помочь»: город ---
    @bot.on_message(is_state(VolunteerStates.WAIT_CITY))
    async def _volunteer_city(msg: aiomax.Message, cursor: aiomax.FSMCursor):
        city = (getattr(msg, "text", None) or getattr(msg, "content", "") or "").strip()
        if not city:
            await msg.reply("Пусто. Напишите город.")
            return

        # TODO: backend.profile_save_city(msg.user_id, city)

        # Если пришли сюда из ленты — вернуть к ленте
        if _pop_return_to_feed(msg.user_id):
            msg.bot.storage.change_state(msg.user_id, VolunteerStates.MAIN_MENU)
            await msg.reply(f"Город обновлён: {city}.")
            await _show_feed(lambda text, keyboard=None: msg.reply(text, keyboard=keyboard))
            return

        # Обычный поток регистрации
        msg.bot.storage.change_state(msg.user_id, VolunteerStates.WAIT_INTERESTS)
        await msg.reply(
            f"Город получен: {city}.\n\nТеперь укажите ваши интересы (чем готовы помочь) одним сообщением."
        )

    # --- ветка «Хочу помочь»: интересы ---
    @bot.on_message(is_state(VolunteerStates.WAIT_INTERESTS))
    async def _volunteer_interests(msg: aiomax.Message, cursor: aiomax.FSMCursor):
        interests = (getattr(msg, "text", None) or getattr(msg, "content", "") or "").strip()
        if not interests:
            await msg.reply("Пусто. Напишите ваши интересы.")
            return

        # TODO: backend.profile_save_interests(msg.user_id, interests)

        if _pop_return_to_feed(msg.user_id):
            msg.bot.storage.change_state(msg.user_id, VolunteerStates.MAIN_MENU)
            await msg.reply(f"Интересы обновлены: {interests}.")
            await _show_feed(lambda text, keyboard=None: msg.reply(text, keyboard=keyboard))
            return

        msg.bot.storage.change_state(msg.user_id, VolunteerStates.MAIN_MENU)
        kb = volunteer_main_menu_keyboard()
        await msg.reply(
            f"Интересы получены: {interests}.\n\nРегистрация завершена. Спасибо!\n\nЧем хотите заняться?",
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
