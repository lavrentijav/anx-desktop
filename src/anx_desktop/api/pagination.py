"""Generic path-based pagination for ``PageableResponse<T>``.

``docs/api.md`` §3.4 defines exactly one pagination style: a 1-based page
number embedded in the path, with an envelope containing ``content``,
``current_page``, ``total_count`` and ``total_page_count``.  There is no
cursor, limit or offset API, and this module intentionally does not invent one.

Stop rules from the docs:

* stop when ``content`` is empty;
* stop when ``current_page >= total_page_count``;
* the envelope does not define a sentinel for the last page.

The connector additionally treats a missing/zero ``total_page_count`` as
"unknown" and continues until an empty page or ``max_pages`` is reached.  This
avoids truncating the first page of a tolerant response where the server omitted
the counter.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Generic, TypeVar

from .models import PageableResponse

T = TypeVar("T")


class Paginator(Generic[T]):
    """Iterate over pages/items using only the documented page-number API.

    Parameters
    ----------
    fetch_page:
        Callable that requests one page.  It must return a
        :class:`~anx_desktop.api.models.PageableResponse`.
    start_page:
        1-based page number to start from.
    max_pages:
        Optional safety bound for tolerant servers that omit
        ``total_page_count``.  It is not part of the Anixart API.

    Examples
    --------
    >>> paginator = Paginator(lambda page: client.feed.get_feed(page))
    >>> for article in paginator:
    ...     print(article.id)
    """

    def __init__(
        self,
        fetch_page: Callable[[int], PageableResponse[T]],
        *,
        start_page: int = 1,
        max_pages: int | None = None,
    ) -> None:
        if start_page < 1:
            raise ValueError("page numbers are 1-based")
        if max_pages is not None and max_pages < 1:
            raise ValueError("max_pages must be positive")
        self._fetch_page = fetch_page
        self._start_page = start_page
        self._max_pages = max_pages

    def pages(self) -> Iterator[PageableResponse[T]]:
        """Yield raw page envelopes, respecting the documented stop rules."""

        page_number = self._start_page
        yielded = 0

        while True:
            if self._max_pages is not None and yielded >= self._max_pages:
                return

            page = self._fetch_page(page_number)
            yielded += 1
            yield page

            if not page.content:
                return
            if page.total_page_count > 0 and page.current_page >= page.total_page_count:
                return

            page_number += 1

    def __iter__(self) -> Iterator[T]:
        """Yield items from all pages in order."""

        for page in self.pages():
            yield from page.content

    def items(self) -> Iterator[T]:
        """Alias for :meth:`__iter__` for readability at call sites."""

        return iter(self)

    def collect(self) -> list[T]:
        """Materialise every item.  Use only for bounded result sets."""

        return list(self)


def paginate(
    fetch_page: Callable[[int], PageableResponse[T]],
    *,
    start_page: int = 1,
    max_pages: int | None = None,
) -> Paginator[T]:
    """Convenience factory mirroring the :class:`Paginator` constructor."""

    return Paginator(fetch_page, start_page=start_page, max_pages=max_pages)


__all__ = ["Paginator", "paginate"]
