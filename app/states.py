"""FSM states for the bot."""

class CommonStates:
    """Общие состояния."""
    IDLE = "idle"

class HelpRequestStates:
    """Состояния для тех, кто выбрал 'Нужна помощь'."""
    WAIT_DESCRIPTION = "help_request:wait_description"

class VolunteerStates:
    """Состояния для волонтёров ('Хочу помочь')."""
    WAIT_CITY = "volunteer:wait_city"
    WAIT_INTERESTS = "volunteer:wait_interests"
    MAIN_MENU = "volunteer:main_menu"  # Новое состояние для главного меню волонтёра
