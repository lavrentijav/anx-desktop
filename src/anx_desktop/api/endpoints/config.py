"""Bootstrap/config endpoints — ``docs/api.md`` §5.12.1 (S#103–S#105)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import AnixPlayerConfigResponse, ConfigUrlsResponse, TogglesResponse

if TYPE_CHECKING:
    from ..client import AnixartClient


class ConfigEndpoints:
    """Config and feature-flag calls.

    ``/config/urls`` and ``/config/toggles`` are authenticated with the
    token query parameter, but the docs explicitly allow an empty token before
    login (§4.11, §5.12.1).  They therefore use ``require_token=False`` and
    send ``token=`` when no session exists.
    """

    def __init__(self, client: AnixartClient) -> None:
        self._client = client

    def get_urls(self, *, version_code: int | None = None, is_beta: bool | None = None) -> ConfigUrlsResponse:
        """``GET /config/urls`` — §5.12.1 (S#105).

        The response is a plain object with **no** ``code`` field (§6.10).
        Mirror ordering and health checks are ``UNKNOWN`` (§9 U-14); this
        method only returns the documented shape.
        """

        return self._client._request_model(
            ConfigUrlsResponse,
            "GET",
            "/config/urls",
            params={"version_code": version_code, "is_beta": is_beta},
            authenticated=True,
            require_token=False,
            send_empty_token=True,
            idempotent=True,
        )

    def get_toggles(
        self,
        *,
        version_code: int | None = None,
        is_beta: bool | None = None,
        is_api_alt: bool | None = None,
    ) -> TogglesResponse:
        """``GET /config/toggles`` — §5.12.1 (S#104)."""

        return self._client._request_model(
            TogglesResponse,
            "GET",
            "/config/toggles",
            params={
                "version_code": version_code,
                "is_beta": is_beta,
                "is_api_alt": is_api_alt,
            },
            authenticated=True,
            require_token=False,
            send_empty_token=True,
            idempotent=True,
        )

    def get_anixplayer_config(self) -> AnixPlayerConfigResponse:
        """``GET /config/anixplayer`` — public endpoint, §5.12.1 (S#103)."""

        return self._client._request_model(
            AnixPlayerConfigResponse,
            "GET",
            "/config/anixplayer",
            authenticated=False,
            idempotent=True,
        )


__all__ = ["ConfigEndpoints"]
