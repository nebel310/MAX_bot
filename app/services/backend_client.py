import os, httpx, logging
from typing import Any

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3001")

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")


class BackendClient:
    def __init__(self):
        self._client = httpx.AsyncClient(base_url=BACKEND_URL, timeout=10)

    async def login(self, max_user_id: int, username: str | None) -> dict:
        payload = {
            "max_user_id": str(max_user_id),  # backend expects string
            "username": (username or f"user_{max_user_id}")
        }
        resp = await self._client.post("/auth/login", json=payload)
        if resp.status_code >= 400:
            # Логируем тело ошибки для диагностики (422 валидация схемы)
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error("Login failed: status=%s payload=%s error=%s", resp.status_code, payload, err)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Login success: user_id=%s token_prefix=%s", max_user_id, data.get("session_token", "")[:10])
        return data

    async def get_feed(self, token: str):
        # пример: защищённый вызов
        resp = await self._client.get("/applications/", headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        return resp.json()

    # ===== Профиль пользователя / интерфейс сначала, потом бизнес-логика =====
    async def get_user_profile(self, token: str) -> dict:
        """Получить профиль текущего пользователя (список интересов — строки).

        Интерфейсный слой: ошибки логируем и пробрасываем наружу, чтобы хендлер
        мог показать user-friendly сообщение. """
        resp = await self._client.get("/user/profile", headers={"Authorization": f"Bearer {token}"})
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error("Get profile failed: status=%s error=%s", resp.status_code, err)
        resp.raise_for_status()
        return resp.json()

    async def get_city(self, city_id: int) -> dict:
        """Получить данные города по ID. Эндпоинт не требует авторизации."""
        resp = await self._client.get(f"/cities/{city_id}")
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error("Get city failed: city_id=%s status=%s error=%s", city_id, resp.status_code, err)
        resp.raise_for_status()
        return resp.json()

    async def get_cities(self, page: int = 1, page_size: int = 100) -> list[dict]:
        """Получить список городов (для сопоставления ввода пользователя)."""
        resp = await self._client.get(f"/cities?page={page}&page_size={page_size}")
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error("Get cities failed: status=%s error=%s", resp.status_code, err)
        resp.raise_for_status()
        return resp.json()

    async def update_user_profile_city(self, token: str, city_id: int) -> dict | None:
        """Частично обновить профиль: только city_id. Возвращает профиль или None при ошибке."""
        payload = {"city_id": city_id}
        resp = await self._client.patch(
            "/user/profile/update",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error("Update city failed: city_id=%s status=%s error=%s", city_id, resp.status_code, err)
            return None
        return resp.json()

    # ===== Теги (интересы) пользователя =====
    async def get_tags(self, page: int = 1, page_size: int = 100) -> list[dict]:
        """Получить список тегов-интересов."""
        resp = await self._client.get(f"/tags?page={page}&page_size={page_size}")
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error("Get tags failed: status=%s error=%s", resp.status_code, err)
        resp.raise_for_status()
        return resp.json()

    async def update_user_interests(self, token: str, tag_ids: list[int]) -> dict | None:
        """Обновить интересы пользователя (перезапись списка). Возвращает dict результата или None."""
        payload = {"tag_ids": tag_ids}
        resp = await self._client.post(
            "/user/interests",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error("Update interests failed: tag_ids=%s status=%s error=%s", tag_ids, resp.status_code, err)
            return None
        return resp.json()

    # ===== Лента событий =====
    async def get_events_feed(
        self,
        token: str,
        include_tag_ids: list[int] | None = None,
        page: int = 1,
        page_size: int = 5,
    ) -> dict:
        """Получить ленту событий. Возвращает dict с ключами events, total_count и т.д.

        include_tag_ids: если список не пуст — передаём как include_tags=1,2,3.
        """
        params = {"page": str(page), "page_size": str(page_size)}
        if include_tag_ids:
            params["include_tags"] = ",".join(str(tid) for tid in include_tag_ids)
        resp = await self._client.get(
            "/events/feed",
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error(
                "Get events feed failed: status=%s params=%s error=%s",
                resp.status_code,
                params,
                err,
            )
        resp.raise_for_status()
        return resp.json()

    async def create_application(self, token: str, event_id: int) -> dict:
        """Создать отклик на событие."""
        payload = {"event_id": event_id}
        resp = await self._client.post(
            "/applications/create",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error("Create application failed: event_id=%s status=%s error=%s", event_id, resp.status_code, err)
        resp.raise_for_status()
        return resp.json()

    async def get_event_details(self, token: str, event_id: int) -> dict:
        """Получить детали события для подтверждения отклика."""
        resp = await self._client.get(
            f"/events/{event_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error("Get event details failed: event_id=%s status=%s error=%s", event_id, resp.status_code, err)
        resp.raise_for_status()
        return resp.json()

    # ===== Лента фондов и донаты =====
    async def get_funds_feed(
        self,
        token: str,
        page: int = 1,
        page_size: int = 5,
    ) -> dict:
        """Получить ленту фондов (активные фонды). Возвращает dict с ключами funds, total_count и т.д."""
        params = {"page": str(page), "page_size": str(page_size)}
        resp = await self._client.get(
            "/funds/feed",
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error(
                "Get funds feed failed: status=%s params=%s error=%s",
                resp.status_code,
                params,
                err,
            )
        resp.raise_for_status()
        return resp.json()

    async def donate_to_fund(self, token: str, fund_id: int, amount: int) -> dict:
        """Сделать донат в фонд."""
        payload = {"fund_id": fund_id, "amount": amount}
        resp = await self._client.post(
            "/funds/donate",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error(
                "Donate failed: fund_id=%s amount=%s status=%s error=%s",
                fund_id,
                amount,
                resp.status_code,
                err,
            )
        resp.raise_for_status()
        return resp.json()

    # ===== Админ: роль и создание =====
    async def check_user_role(self, token: str) -> dict | None:
        """Проверить текущую роль пользователя (user/admin)."""
        resp = await self._client.get(
            "/admin/check-role",
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error("Check role failed: status=%s error=%s", resp.status_code, err)
            return None
        return resp.json()

    async def create_admin(self, token: str, max_user_id: int) -> dict | None:
        """Создать администратора (если бекенд разрешит)."""
        payload = {"max_user_id": str(max_user_id)}
        resp = await self._client.post(
            "/admin/admins/create",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error("Create admin failed: user_id=%s status=%s error=%s", max_user_id, resp.status_code, err)
            return None
        return resp.json()

    # ===== Создание фонда (админ) =====
    async def create_fund(self, token: str, payload: dict) -> dict | None:
        """Создать фонд. payload должен соответствовать SFundCreate."""
        resp = await self._client.post(
            "/funds/create",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error("Create fund failed: title=%s status=%s error=%s", payload.get("title"), resp.status_code, err)
            return None
        return resp.json()

    # ===== Создание события (админ) =====
    async def create_event(self, token: str, payload: dict) -> dict | None:
        """Создать новое мероприятие. payload соответствует SEventCreate."""
        resp = await self._client.post(
            "/events/create",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error(
                "Create event failed: title=%s status=%s error=%s",
                payload.get("title"),
                resp.status_code,
                err,
            )
            return None
        return resp.json()

    # ===== Админ: собственные мероприятия =====
    async def get_my_events(
        self,
        token: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict | None:
        """Получить список мероприятий, созданных текущим пользователем (админом).

        Ожидаемый ответ: {"events": [...], "total_count": N}
        Возвращает dict или None при ошибке.
        """
        params = {"page": str(page), "page_size": str(page_size)}
        resp = await self._client.get(
            "/events/my-events",
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error(
                "Get my events failed: status=%s params=%s error=%s",
                resp.status_code,
                params,
                err,
            )
            return None
        return resp.json()

    # ===== Админ: отклики на событие =====
    async def get_event_applications(
        self,
        token: str,
        event_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> dict | list | None:
        """Получить отклики (applications) на конкретное мероприятие.

        Эндпоинт: /applications/event/{event_id}
        Допускаем два типа ответа:
          - {"applications": [...]} (dict)
          - [...] (list напрямую)
        Возвращаем исходную структуру или None при ошибке.
        """
        params = {"page": str(page), "page_size": str(page_size)}
        resp = await self._client.get(
            f"/applications/event/{event_id}",
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error(
                "Get event applications failed: event_id=%s status=%s params=%s error=%s",
                event_id,
                resp.status_code,
                params,
                err,
            )
            return None
        try:
            data = resp.json()
        except Exception:
            logger.error("Get event applications failed: invalid JSON event_id=%s", event_id)
            return None
        return data

    # ===== Админ: модерация отклика =====
    async def update_application(self, token: str, application_id: int, status: str, rejection_reason: str | None = None) -> dict | None:
        """Обновить статус отклика (approved / rejected) с опциональной причиной.

        Эндпоинт: PUT /applications/{application_id}/update
        Схема: SApplicationUpdate { status: str, rejection_reason?: str|null }
        """
        payload: dict[str, Any] = {"status": status}
        if rejection_reason is not None and rejection_reason.strip():
            payload["rejection_reason"] = rejection_reason.strip()
        resp = await self._client.put(
            f"/applications/{application_id}/update",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error(
                "Update application failed: application_id=%s status_field=%s status=%s error=%s",
                application_id,
                status,
                resp.status_code,
                err,
            )
            return None
        try:
            return resp.json()
        except Exception as e_json:
            logger.error("Update application failed: invalid JSON application_id=%s error=%s", application_id, e_json)
            return None

    # ===== Волонтёр: мои отклики =====
    async def get_my_applications(
        self,
        token: str,
        page: int = 1,
        page_size: int = 10,
    ) -> dict | None:
        """Получить собственные отклики текущего пользователя.

        Эндпоинт: /applications/my-applications -> SApplicationListResponse
        Формат ожидаемого ответа: {
          "applications": [SApplicationWithEvent...],
          "total_count": int,
          ...
        }
        Возвращаем dict или None при ошибке.
        """
        params = {"page": str(page), "page_size": str(page_size)}
        resp = await self._client.get(
            "/applications/my-applications",
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error(
                "Get my applications failed: status=%s params=%s error=%s",
                resp.status_code,
                params,
                err,
            )
            return None
        try:
            return resp.json()
        except Exception as e_json:
            logger.error("Get my applications failed: invalid JSON error=%s", e_json)
            return None

    # ===== Лидерборд волонтёров =====
    async def get_leaderboard(
        self,
        token: str,
        top_n: int = 10,
    ) -> dict | None:
        """Получить лидерборд (топ пользователей + позиция текущего).

        Эндпоинт: /user/leaderboard -> SLeaderboard
        Параметры: top_n (1..100)
        Ожидаемый формат ответа:
        {
          "top_users": [
             {"user_id": int, "username": str, "rating": int, "participation_count": int, "position": int},
             ...
          ],
          "current_user_position": { ... } | null
        }
        Возвращаем dict или None при ошибке.
        """
        params = {"top_n": str(top_n)}
        resp = await self._client.get(
            "/user/leaderboard",
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            logger.error(
                "Get leaderboard failed: status=%s params=%s error=%s",
                resp.status_code,
                params,
                err,
            )
            return None
        try:
            return resp.json()
        except Exception as e_json:
            logger.error("Get leaderboard failed: invalid JSON error=%s", e_json)
            return None

backend_client = BackendClient()