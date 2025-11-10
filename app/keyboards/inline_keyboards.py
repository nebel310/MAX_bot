"""Inline keyboards (callback buttons) using official aiomax API.

According to docs: use `aiomax.buttons.KeyboardBuilder` and `CallbackButton`.
Sending: pass built keyboard directly as `keyboard=kb` when replying/sending.
Callbacks handled with `@bot.on_button_callback(lambda data: data.payload == '...')`.
"""

import aiomax.buttons

def role_selection_keyboard() -> aiomax.buttons.KeyboardBuilder:
    """Клавиатура выбора роли при старте."""
    kb = aiomax.buttons.KeyboardBuilder()
    kb.row(
        aiomax.buttons.CallbackButton(text="Нужна помощь", payload="need_help"),
        aiomax.buttons.CallbackButton(text="Хочу помочь", payload="want_help"),
    )
    return kb

def volunteer_main_menu_keyboard() -> aiomax.buttons.KeyboardBuilder:
    """Главное меню для волонтёра после регистрации."""
    kb = aiomax.buttons.KeyboardBuilder()
    kb.row(
        aiomax.buttons.CallbackButton(text="Лента заявок", payload="feed"),
    )
    kb.row(
        aiomax.buttons.CallbackButton(text="Мой профиль", payload="profile"),
        aiomax.buttons.CallbackButton(text="Помощь", payload="help"),
    )
    return kb

def feed_actions_keyboard() -> aiomax.buttons.KeyboardBuilder:
    """Клавиатура действий в ленте заявок."""
    kb = aiomax.buttons.KeyboardBuilder()
    kb.row(
        aiomax.buttons.CallbackButton(text="Подробнее 1", payload="details_1"),
    )
    kb.row(
        aiomax.buttons.CallbackButton(text="Изменить фильтры", payload="change_filters"),
        aiomax.buttons.CallbackButton(text="Изменить город", payload="change_city"),
    )
    return kb

def request_details_keyboard() -> aiomax.buttons.KeyboardBuilder:
    """Клавиатура для детального просмотра заявки."""
    kb = aiomax.buttons.KeyboardBuilder()
    kb.row(
        aiomax.buttons.CallbackButton(text="Откликнуться", payload="respond"),
    )
    kb.row(
        aiomax.buttons.CallbackButton(text="Назад к заявкам", payload="back_to_feed"),
    )
    return kb

def response_confirmation_keyboard() -> aiomax.buttons.KeyboardBuilder:
    """Клавиатура после отклика на заявку."""
    kb = aiomax.buttons.KeyboardBuilder()
    kb.row(
        aiomax.buttons.CallbackButton(text="Вернуться к ленте", payload="back_to_feed"),
    )
    return kb

__all__ = [
    "role_selection_keyboard", 
    "volunteer_main_menu_keyboard", 
    "feed_actions_keyboard",
    "request_details_keyboard",
    "response_confirmation_keyboard"
]
