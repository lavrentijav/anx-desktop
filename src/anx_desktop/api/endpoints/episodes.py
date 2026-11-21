"""Episodes, sources and watch progress — ``docs/api.md`` §5.6.1 (checklist row 6)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import (
    EpisodeResponse,
    EpisodeTargetResponse,
    EpisodeUnwatchResponse,
    EpisodeUpdate,
    EpisodeWatchResponse,
    PageableResponse,
    SourcesResponse,
    TypesResponse,
)

if TYPE_CHECKING:
    from ..client import AnixartClient


class EpisodeEndpoints:
    """Episode type/source/episode queries and watch-state mutations."""

    def __init__(self, client: AnixartClient) -> None:
        self._client = client

    def get_types(self, release_id: int) -> TypesResponse:
        """``GET /episode/{releaseId}`` — §5.6.1 (S#117)."""

        return self._client._request_model(
            TypesResponse,
            "GET",
            f"/episode/{release_id}",
            idempotent=True,
        )

    def get_sources(self, release_id: int, type_id: int) -> SourcesResponse:
        """``GET /episode/{releaseId}/{typeId}`` — public, §5.6.1 (S#118)."""

        return self._client._request_model(
            SourcesResponse,
            "GET",
            f"/episode/{release_id}/{type_id}",
            authenticated=False,
            idempotent=True,
        )

    def get_episodes(
        self,
        release_id: int,
        type_id: int,
        source_id: int,
        *,
        sort: int | None = None,
    ) -> EpisodeResponse:
        """``GET /episode/{releaseId}/{typeId}/{sourceId}`` — §5.6.1 (S#119)."""

        return self._client._request_model(
            EpisodeResponse,
            "GET",
            f"/episode/{release_id}/{type_id}/{source_id}",
            params={"sort": sort},
            idempotent=True,
        )

    def get_updates(self, release_id: int, page: int = 1) -> PageableResponse[EpisodeUpdate]:
        """``GET /episode/updates/{releaseId}/{page}`` — public, §5.6.1 (S#114)."""

        return self._client._request_model(
            PageableResponse[EpisodeUpdate],
            "GET",
            f"/episode/updates/{release_id}/{page}",
            authenticated=False,
            idempotent=True,
        )

    def watch(self, release_id: int, source_id: int, position: int | None = None) -> EpisodeWatchResponse:
        """``POST /episode/watch/{releaseId}/{sourceId}[/{position}]`` — §5.6.1 (S#115/S#116).

        This is a mutation, so it is never retried.
        """

        path = f"/episode/watch/{release_id}/{source_id}"
        if position is not None:
            path = f"{path}/{position}"
        return self._client._request_model(
            EpisodeWatchResponse,
            "POST",
            path,
            idempotent=False,
        )

    def unwatch(
        self, release_id: int, source_id: int, position: int | None = None
    ) -> EpisodeUnwatchResponse:
        """``POST /episode/unwatch/{releaseId}/{sourceId}[/{position}]`` — §5.6.1 (S#112/S#113)."""

        path = f"/episode/unwatch/{release_id}/{source_id}"
        if position is not None:
            path = f"{path}/{position}"
        return self._client._request_model(
            EpisodeUnwatchResponse,
            "POST",
            path,
            idempotent=False,
        )

    def get_target(self, release_id: int, source_id: int, position: int) -> EpisodeTargetResponse:
        """``GET /episode/target/{releaseId}/{sourceId}/{position}`` — §5.6.1 (S#111).

        The payload was recovered from a live 11 BETA 2 capture (2026-11-08):
        it contains an ``episode`` object with ``url``/``iframe``/``quality``
        and the nested release/source, so the response can be modelled instead
        of raising ``NotImplementedError``.
        """

        return self._client._request_model(
            EpisodeTargetResponse,
            "GET",
            f"/episode/target/{release_id}/{source_id}/{position}",
            idempotent=True,
        )


__all__ = ["EpisodeEndpoints"]
