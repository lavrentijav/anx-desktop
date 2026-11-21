"""Search and catalog filter — ``docs/api.md`` §5.5 and §5.8.2 (checklist row 7)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import (
    FilterRequest,
    PageableResponse,
    Release,
    ReleaseSearchResponse,
    SearchRequest,
)

if TYPE_CHECKING:
    from ..client import AnixartClient


class SearchEndpoints:
    """Release search and the paged catalog filter."""

    def __init__(self, client: AnixartClient) -> None:
        self._client = client

    def search_releases(
        self,
        page: int,
        query: str,
        *,
        search_by: int = 0,
    ) -> ReleaseSearchResponse:
        """``POST /search/releases/{page}`` — §5.8.2 (S#301).

        The response is **not** a ``PageableResponse``: the docs specify
        ``ReleaseSearchResponse {releases, related}`` (§6.1, reconciliation
        note in §1.5).  ``API-Version: v2`` is required by the client.
        """

        body = SearchRequest.model_validate({"query": query, "searchBy": search_by})
        return self._client._request_model(
            ReleaseSearchResponse,
            "POST",
            f"/search/releases/{page}",
            json_body=body.model_dump(by_alias=True, exclude_none=True),
            headers={"API-Version": "v2"},
            idempotent=True,
        )

    def filter_releases(
        self,
        page: int = 1,
        request: FilterRequest | None = None,
        *,
        extended_mode: bool | None = None,
    ) -> PageableResponse[Release]:
        """``POST /filter/{page}`` — §5.5 (S#127).

        The body is ``FilterRequest`` (§6.11); all fields are optional and
        ``sort`` defaults to ``0``.  An omitted request sends an empty JSON
        object rather than inventing filter values.
        """

        body = (
            request.model_dump(by_alias=True, exclude_none=True)
            if request is not None
            else {}
        )
        return self._client._request_model(
            PageableResponse[Release],
            "POST",
            f"/filter/{page}",
            params={"extended_mode": extended_mode},
            json_body=body,
            idempotent=True,
        )


__all__ = ["SearchEndpoints"]
