"""FSM states for the bot."""

class CommonStates:
    """Общие состояния."""
    IDLE = "idle"

class HelpRequestStates:
    """Состояния для тех, кто выбрал 'Нужна помощь'."""
    WAIT_DESCRIPTION = "help_request:wait_description"
    WAIT_FUND_INFO = "help_request:wait_fund_info"  # Ввод данных нового фонда

class AdminStates:
    """Состояния для админских действий (создание событий и пр.)"""
    WAIT_EVENT_INFO = "admin:wait_event_info"  # зарезервировано под будущее создание события
    WAIT_EVENT_APPS_EVENT_ID = "admin:wait_event_apps_event_id"  # ожидание ввода ID события для просмотра откликов
    WAIT_EVENT_CITY = "admin:wait_event_city"  # ожидание ввода города, если не указан при создании события

class VolunteerStates:
    """Состояния для волонтёров ('Хочу помочь')."""
    WAIT_CITY = "volunteer:wait_city"
    WAIT_INTERESTS = "volunteer:wait_interests"
    MAIN_MENU = "volunteer:main_menu"  # Новое состояние для главного меню волонтёра
    WAIT_EVENT_ID = "volunteer:wait_event_id"  # Ожидание ввода ID события для отклика
    WAIT_FUND_ID = "volunteer:wait_fund_id"  # Ожидание ввода ID фонда для доната
    WAIT_DONATION_AMOUNT = "volunteer:wait_donation_amount"  # Ожидание суммы доната
