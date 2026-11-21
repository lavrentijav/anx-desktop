"""Notification count/list — ``docs/api.md`` §5.10.1 (checklist row 12)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import (
    NotificationCountResponse,
    PageableResponse,
    ProfileNotification,
    Response,
)

if TYPE_CHECKING:
    from ..client import AnixartClient


class NotificationEndpoints:
    """Base notification list and count.

    Typed subtype lists (article/friend/episode/etc.) are separate endpoints
    in §5.10.1; the union payload has no discriminator (§6.9), so the base
    model exposes the known optional subtype fields and ignores the rest.
    """

    def __init__(self, client: AnixartClient) -> None:
        self._client = client

    def get_count(self) -> NotificationCountResponse:
        """``GET /notification/count`` — §5.10.1 (S#140)."""

        return self._client._request_model(
            NotificationCountResponse,
            "GET",
            "/notification/count",
            idempotent=True,
        )

    def get_all(self, page: int = 1) -> PageableResponse[ProfileNotification]:
        """``GET /notification/all/{page}`` — §5.10.1 (S#133)."""

        return self._client._request_model(
            PageableResponse[ProfileNotification],
            "GET",
            f"/notification/all/{page}",
            idempotent=True,
        )

    def mark_all_read(self) -> Response:
        """``GET /notification/read`` — mutation, §5.10.1 (S#148)."""

        return self._client._request_model(
            Response,
            "GET",
            "/notification/read",
            idempotent=False,
        )

    def delete_all(self) -> Response:
        """``GET /notification/delete/all`` — mutation, §5.10.1 (S#141)."""

        return self._client._request_model(
            Response,
            "GET",
            "/notification/delete/all",
            idempotent=False,
        )


__all__ = ["NotificationEndpoints"]
