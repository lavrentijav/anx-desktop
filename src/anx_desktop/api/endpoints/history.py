"""History and watch progress — ``docs/api.md`` §5.6.2 (checklist row 9)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import HistoryResponse, PageableResponse, Release

if TYPE_CHECKING:
    from ..client import AnixartClient


class HistoryEndpoints:
    """Paged history and the two history mutation calls."""

    def __init__(self, client: AnixartClient) -> None:
        self._client = client

    def get_history(self, page: int = 1) -> PageableResponse[Release]:
        """``GET /history/{page}`` — §5.6.2 (S#130)."""

        return self._client._request_model(
            PageableResponse[Release],
            "GET",
            f"/history/{page}",
            idempotent=True,
        )

    def add(
        self,
        release_id: int,
        source_id: int,
        position: int,
    ) -> HistoryResponse:
        """``GET /history/add/{r_id}/{s_id}/{position}`` — mutation, §5.6.2 (S#128).

        The docs do not specify whether ``position`` is an episode position or
        seconds (§10.3 "History / progress"); it is passed through unchanged.
        """

        return self._client._request_model(
            HistoryResponse,
            "GET",
            f"/history/add/{release_id}/{source_id}/{position}",
            idempotent=False,
        )

    def delete(self, release_id: int) -> HistoryResponse:
        """``GET /history/delete/{r_id}`` — mutation, §5.6.2 (S#129)."""

        return self._client._request_model(
            HistoryResponse,
            "GET",
            f"/history/delete/{release_id}",
            idempotent=False,
        )


__all__ = ["HistoryEndpoints"]
