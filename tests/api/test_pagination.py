"""Pagination tests: only the documented page-number scheme is used."""

from __future__ import annotations

import httpx
import pytest

from anx_desktop.api import PageableResponse, Paginator, Release


def _page(current: int, total: int, ids: list[int]) -> PageableResponse[Release]:
    return PageableResponse[Release].model_validate(
        {
            "code": 0,
            "content": [{"id": release_id} for release_id in ids],
            "current_page": current,
            "total_count": len(ids) * total,
            "total_page_count": total,
        }
    )


def test_paginator_stops_at_total_page_count():
    requested: list[int] = []

    def fetch(page: int) -> PageableResponse[Release]:
        requested.append(page)
        return _page(page, total=3, ids=[page * 10, page * 10 + 1])

    items = list(Paginator(fetch))
    assert requested == [1, 2, 3]
    assert [item.id for item in items] == [10, 11, 20, 21, 30, 31]


def test_paginator_stops_on_empty_content():
    requested: list[int] = []

    def fetch(page: int) -> PageableResponse[Release]:
        requested.append(page)
        if page == 1:
            return _page(1, total=5, ids=[1, 2])
        return _page(page, total=5, ids=[])

    items = list(Paginator(fetch))
    assert requested == [1, 2]
    assert [item.id for item in items] == [1, 2]


def test_paginator_with_unknown_total_continues_until_empty():
    requested: list[int] = []

    def fetch(page: int) -> PageableResponse[Release]:
        requested.append(page)
        if page == 1:
            return _page(1, total=0, ids=[1])
        return _page(page, total=0, ids=[])

    items = list(Paginator(fetch))
    assert requested == [1, 2]
    assert [item.id for item in items] == [1]


def test_paginator_max_pages_guard():
    requested: list[int] = []

    def fetch(page: int) -> PageableResponse[Release]:
        requested.append(page)
        return _page(page, total=0, ids=[page])

    items = list(Paginator(fetch, max_pages=2))
    assert requested == [1, 2]
    assert len(items) == 2


def test_paginator_rejects_zero_start_page():
    with pytest.raises(ValueError):
        Paginator(lambda page: _page(page, 1, []), start_page=0)


def test_paginator_integration_with_feed_endpoint(client_factory):
    requested: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(int(request.url.path.rsplit("/", 1)[-1]))
        assert request.url.params["token"] == "secret-token"
        current = requested[-1]
        if current == 1:
            content = [{"id": 1}, {"id": 2}]
            total_pages = 2
        else:
            content = [{"id": 3}]
            total_pages = 2
        return httpx.Response(
            200,
            json={
                "code": 0,
                "content": content,
                "current_page": current,
                "total_count": 3,
                "total_page_count": total_pages,
            },
        )

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    items = list(Paginator(lambda page: client.feed.get_feed(page)))

    assert requested == [1, 2]
    assert [item.id for item in items] == [1, 2, 3]
