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
        aiomax.buttons.CallbackButton(text="Лента фондов", payload="funds"),
    )
    kb.row(
        aiomax.buttons.CallbackButton(text="Мой профиль", payload="profile"),
        aiomax.buttons.CallbackButton(text="Помощь", payload="help"),
    )
    return kb

def profile_keyboard() -> aiomax.buttons.KeyboardBuilder:
    """Клавиатура при просмотре профиля: лента, помощь, редактирование."""
    kb = aiomax.buttons.KeyboardBuilder()
    kb.row(
        aiomax.buttons.CallbackButton(text="Лента заявок", payload="feed"),
        aiomax.buttons.CallbackButton(text="Помощь", payload="help"),
    )
    kb.row(
        aiomax.buttons.CallbackButton(text="Редактировать профиль", payload="edit_profile"),
        aiomax.buttons.CallbackButton(text="Мои отклики", payload="my_applications"),
    )
    kb.row(
        aiomax.buttons.CallbackButton(text="Лидерборд", payload="leaderboard"),
    )
    return kb

def event_item_keyboard() -> aiomax.buttons.KeyboardBuilder:
    """Клавиатура под отдельным событием в ленте: отклик / назад."""
    kb = aiomax.buttons.KeyboardBuilder()
    kb.row(
        aiomax.buttons.CallbackButton(text="Откликнуться", payload="respond"),
        aiomax.buttons.CallbackButton(text="Назад", payload="back_to_main_menu"),
    )
    return kb

def fund_item_keyboard() -> aiomax.buttons.KeyboardBuilder:
    """Клавиатура под отдельным фондом: пожертвовать / назад."""
    kb = aiomax.buttons.KeyboardBuilder()
    kb.row(
        aiomax.buttons.CallbackButton(text="Пожертвовать", payload="donate"),
        aiomax.buttons.CallbackButton(text="Назад", payload="back_to_main_menu"),
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
    kb.row(
        aiomax.buttons.CallbackButton(text="Назад", payload="back_to_main_menu"),
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

def donation_confirmation_keyboard() -> aiomax.buttons.KeyboardBuilder:
    """Клавиатура после успешного доната."""
    kb = aiomax.buttons.KeyboardBuilder()
    kb.row(
        aiomax.buttons.CallbackButton(text="К фондам", payload="back_to_funds"),
        aiomax.buttons.CallbackButton(text="Главное меню", payload="back_to_main_menu"),
    )
    return kb

def admin_fund_main_keyboard() -> aiomax.buttons.KeyboardBuilder:
    """Главное меню администратора фондов после регистрации фонда."""
    kb = aiomax.buttons.KeyboardBuilder()
    kb.row(
        aiomax.buttons.CallbackButton(text="Получить отклики на событие", payload="admin_event_applications"),
    )
    kb.row(
        aiomax.buttons.CallbackButton(text="Создать новое событие", payload="admin_create_event"),
        aiomax.buttons.CallbackButton(text="Помощь", payload="help"),
    )
    return kb

def admin_event_created_keyboard() -> aiomax.buttons.KeyboardBuilder:
    """Клавиатура после успешного создания события админом."""
    kb = aiomax.buttons.KeyboardBuilder()
    kb.row(
        aiomax.buttons.CallbackButton(text="В главное меню", payload="admin_back_to_main"),
    )
    return kb

def admin_help_keyboard() -> aiomax.buttons.KeyboardBuilder:
    """Клавиатура раздела помощи для админа/создателя фондов и событий."""
    kb = aiomax.buttons.KeyboardBuilder()
    kb.row(
        aiomax.buttons.CallbackButton(text="Создать событие", payload="admin_create_event"),
        aiomax.buttons.CallbackButton(text="Отклики на событие", payload="admin_event_applications"),
    )
    kb.row(
        aiomax.buttons.CallbackButton(text="Назад", payload="admin_back_to_main"),
    )
    return kb

def application_moderation_keyboard(application_id: int) -> aiomax.buttons.KeyboardBuilder:
    """Клавиатура модерации отклика (approve / reject)."""
    kb = aiomax.buttons.KeyboardBuilder()
    kb.row(
        aiomax.buttons.CallbackButton(text="✅ Принять", payload=f"app_approve_{application_id}"),
        aiomax.buttons.CallbackButton(text="🚫 Отклонить", payload=f"app_reject_{application_id}"),
    )
    return kb

def my_applications_return_keyboard() -> aiomax.buttons.KeyboardBuilder:
    """Клавиатура возврата из списка собственных откликов."""
    kb = aiomax.buttons.KeyboardBuilder()
    kb.row(
        aiomax.buttons.CallbackButton(text="Профиль", payload="profile"),
        aiomax.buttons.CallbackButton(text="Главное меню", payload="back_to_main_menu"),
    )
    return kb

__all__ = [
    "role_selection_keyboard", 
    "volunteer_main_menu_keyboard", 
    "profile_keyboard",
    "event_item_keyboard",
    "fund_item_keyboard",
    "feed_actions_keyboard",
    "request_details_keyboard",
    "response_confirmation_keyboard",
    "donation_confirmation_keyboard"
    ,"admin_fund_main_keyboard"
    ,"admin_event_created_keyboard"
    ,"admin_help_keyboard"
    ,"application_moderation_keyboard"
    ,"my_applications_return_keyboard"
]
