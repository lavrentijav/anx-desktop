"""Shared offline test fixtures.

Every client in this suite is constructed with ``httpx.MockTransport`` (or
``respx``), so no test can reach the network.  ``sleep`` is replaced by a no-op
to keep retry tests instantaneous.
"""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from anx_desktop.api import AnixartClient, MemoryTokenStore


@pytest.fixture
def client_factory() -> Callable[..., AnixartClient]:
    def factory(
        handler: Callable[[httpx.Request], httpx.Response],
        *,
        token_store: MemoryTokenStore | None = None,
        max_retries: int = 0,
        **kwargs: object,
    ) -> AnixartClient:
        sleep = kwargs.pop("sleep", lambda _: None)
        return AnixartClient(
            "https://api.test",
            transport=httpx.MockTransport(handler),
            token_store=token_store,
            max_retries=max_retries,
            sleep=sleep,  # type: ignore[arg-type]
            **kwargs,  # type: ignore[arg-type]
        )

    return factory
