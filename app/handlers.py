"""Application handlers.

Here we register all bot event handlers via a setup function so that
`main.py` stays focused on initialization/bootstrapping.

Next planned separation:
 - start.py (welcome & onboarding)
 - echo.py (debug / fallback)
 - roles.py (role selection & state)
For now kept together to stay simple while architecture evolves.
"""

from typing import Callable
import aiomax
from app.keyboards.inline_keyboards import role_selection_keyboard
# Using stub service abstraction instead of direct model dict
from app.services.role_stub import (
	set_role,
	UserRole,
	get_role,
	set_start_message_id,
	get_start_message_id,
)

TEST_USER_ID = 89408765  # Ограничиваем тестовую функциональность этим пользователем

# Состояния для сбора данных волонтёра
STATE_VOLUNTEER_WAIT_CITY = "volunteer_wait_city"
STATE_IDLE = "idle"

WELCOME_MESSAGE = (
	"Бот: Добро пожаловать в ДобрыйБот! 👋\n"
	"Здесь вы можете помочь благотворительным фондам или найти волонтеров.\n\n"
	"Выберите вашу роль:"
)


def setup_handlers(bot: aiomax.Bot) -> None:
	"""Register core handlers on the provided bot instance.

	Args:
		bot: The aiomax.Bot instance created in `main.py`.
	"""

	async def _send_welcome(user_id: int, send_callable):
		"""Общий метод отправки приветствия с защитой от повторов.

		Не шлём если уже есть сохранённое стартовое сообщение или выбрана роль.
		"""
		# Вариант B: для TEST_USER_ID всегда отправляем (игнорируем кэш и выбранную роль),
		# для остальных пользователей сохраняем прежнюю защиту от повторов.
		if user_id != TEST_USER_ID and (get_start_message_id(user_id) or get_role(user_id)):
			return
		kb = role_selection_keyboard()
		msg: aiomax.Message = await send_callable(WELCOME_MESSAGE, keyboard=kb)
		if hasattr(msg, "id"):
			set_start_message_id(user_id, msg.id)

	# Событие старта бота (платформа) — первая точка входа
	@bot.on_bot_start()
	async def _on_start(payload: aiomax.BotStartPayload):
		await _send_welcome(payload.user_id, lambda text, keyboard=None: payload.send(text, keyboard=keyboard))

	# Команда /start — ручной перезапуск логики
	@bot.on_message("start")
	async def _start_message(ctx: aiomax.CommandContext):
		await _send_welcome(ctx.user_id, lambda text, keyboard=None: ctx.send(text, keyboard=keyboard))

	async def _finalize_role(cb: aiomax.Callback, role_text: str):
		"""Редактируем сохранённое стартовое сообщение, если его id известен.

		Используем сохранённый message_id, а не cb.message (способ более стабилен при перезапуске процесса).
		"""
		msg_id = get_start_message_id(cb.user_id)
		if not msg_id:
			return
		try:
			# edit_message(signature): edit_message(message_id, text, ...)
			await cb.bot.edit_message(msg_id, role_text)
		except Exception:
			pass

	@bot.on_button_callback(lambda data: data.payload == "need_help")
	async def _need_help(cb: aiomax.Callback):
		# Логика: для НЕ тестового пользователя проверяем роль и выходим если уже есть.
		# Для тестового пользователя проверку роли пропускаем (можно жать снова).
		if cb.user_id != TEST_USER_ID and get_role(cb.user_id):
			return
		set_role(cb.user_id, UserRole.NEED_HELP)
		await _finalize_role(cb, "Вы выбрали роль: Нужна помощь")
		# TODO: перейти к сценарию сбора деталей запроса.

	@bot.on_button_callback(lambda data: data.payload == "want_help")
	async def _want_help(cb: aiomax.Callback):
		if cb.user_id != TEST_USER_ID and get_role(cb.user_id):
			return
		set_role(cb.user_id, UserRole.WANT_HELP)
		await _finalize_role(cb, "Вы выбрали роль: Хочу помочь")
		# Запрашиваем город. Для тестового пользователя не трогаем состояние.
		if cb.user_id != TEST_USER_ID:
			cb.bot.storage.change_state(cb.user_id, STATE_VOLUNTEER_WAIT_CITY)
		await cb.send("Укажите город, в котором готовы помогать (одним сообщением).")
		# TODO: предложить варианты помощи / направления.

	# Сообщение с городом от волонтёра (кроме тестового пользователя)
	@bot.on_message(lambda m: m.user_id != TEST_USER_ID and m.bot.storage.get_state(m.user_id) == STATE_VOLUNTEER_WAIT_CITY)
	async def _volunteer_city(msg: aiomax.Message):
		city = (msg.content or "").strip()
		if not city:
			await msg.reply("Пусто. Напишите название города.")
			return
		# Сохраняем в FSM data (пока без backend)
		msg.bot.storage.change_data(msg.user_id, {"city": city})
		msg.bot.storage.change_state(msg.user_id, STATE_IDLE)
		await msg.reply(f"Город сохранён: {city}. Спасибо! Дальнейшие шаги добавим позже.")

