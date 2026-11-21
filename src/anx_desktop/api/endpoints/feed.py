"""Feed and discovery endpoints — ``docs/api.md`` §5.8.1 and §5.8.3."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import (
    Article,
    Interesting,
    LatestArticleResponse,
    PageableResponse,
    Release,
    ReleaseComment,
)

if TYPE_CHECKING:
    from ..client import AnixartClient


class FeedEndpoints:
    """Article feed and the release discovery cards (checklist §10.1 rows 4)."""

    def __init__(self, client: AnixartClient) -> None:
        self._client = client

    def get_feed(
        self,
        page: int = 1,
        *,
        channel_id: int | None = None,
        date: int | None = None,
    ) -> PageableResponse[Article]:
        """``GET /feed/all/{page}`` — §5.8.3 (S#124).

        ``channel_id`` and ``date`` are optional filters; accepted ``date``
        values are ``UNKNOWN`` (§9 U-22).
        """

        return self._client._request_model(
            PageableResponse[Article],
            "GET",
            f"/feed/all/{page}",
            params={"channel_id": channel_id, "date": date},
            idempotent=True,
        )

    def get_latest_article(self) -> LatestArticleResponse:
        """``GET /feed/latest`` — §5.8.3 (S#125)."""

        return self._client._request_model(
            LatestArticleResponse,
            "GET",
            "/feed/latest",
            idempotent=True,
        )

    def get_latest_articles(self, page: int = 1) -> PageableResponse[Article]:
        """``GET /feed/latest/all/{page}`` — §5.8.3 (S#126)."""

        return self._client._request_model(
            PageableResponse[Article],
            "GET",
            f"/feed/latest/all/{page}",
            idempotent=True,
        )

    def get_interesting(self) -> PageableResponse[Interesting]:
        """``POST /discover/interesting`` — public, §5.8.1 (S#108).

        The endpoint is a read-only POST with no body; retries are safe.
        """

        return self._client._request_model(
            PageableResponse[Interesting],
            "POST",
            "/discover/interesting",
            authenticated=False,
            idempotent=True,
        )

    def get_recommendations(
        self,
        page: int = 1,
        *,
        previous_page: int | None = None,
    ) -> PageableResponse[Release]:
        """``POST /discover/recommendations/{page}`` — §5.8.1 (S#109).

        ``previous_page`` is an optional paging hint whose semantics are
        ``UNKNOWN`` (§3.4).
        """

        return self._client._request_model(
            PageableResponse[Release],
            "POST",
            f"/discover/recommendations/{page}",
            params={"previous_page": previous_page},
            idempotent=True,
        )

    def get_discussing(self) -> PageableResponse[Release]:
        """``POST /discover/discussing`` — §5.8.1 (S#107)."""

        return self._client._request_model(
            PageableResponse[Release],
            "POST",
            "/discover/discussing",
            idempotent=True,
        )

    def get_watching(self, page: int = 1) -> PageableResponse[Release]:
        """``POST /discover/watching/{page}`` — §5.8.1 (S#110)."""

        return self._client._request_model(
            PageableResponse[Release],
            "POST",
            f"/discover/watching/{page}",
            idempotent=True,
        )

    def get_comments_week(self) -> PageableResponse[ReleaseComment]:
        """``POST /discover/comments`` — public, §5.8.1 (S#106)."""

        return self._client._request_model(
            PageableResponse[ReleaseComment],
            "POST",
            "/discover/comments",
            authenticated=False,
            idempotent=True,
        )


__all__ = ["FeedEndpoints"]
