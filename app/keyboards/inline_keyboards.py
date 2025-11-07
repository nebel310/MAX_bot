"""Inline keyboards (callback buttons) using official aiomax API.

According to docs: use `aiomax.buttons.KeyboardBuilder` and `CallbackButton`.
Sending: pass built keyboard directly as `keyboard=kb` when replying/sending.
Callbacks handled with `@bot.on_button_callback(lambda data: data.payload == '...')`.
"""

import aiomax

def role_selection_keyboard() -> aiomax.buttons.KeyboardBuilder:
	"""Create keyboard with role selection buttons.

	Returns a KeyboardBuilder instance ready to be passed as `keyboard`.
	Payloads:
	  - need_help
	  - want_help
	"""
	kb = aiomax.buttons.KeyboardBuilder()
	kb.row(
		aiomax.buttons.CallbackButton("Нужна помощь", "need_help"),
		aiomax.buttons.CallbackButton("Хочу помочь", "want_help"),
	)
	return kb

__all__ = ["role_selection_keyboard"]
