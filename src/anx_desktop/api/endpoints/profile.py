"""Profile core and profile lists — ``docs/api.md`` §5.2.1 and §5.2.8.

Checklist rows 2, 3 and 10 in §10.1.  The rest of the large profile domain
(preferences mutations, friends, badges, enforcement) is intentionally not
exposed yet; schemas or semantics marked ``UNKNOWN`` must not be guessed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import (
    PageableResponse,
    ProfileInfoResponse,
    ProfileListResponse,
    ProfileListStatus,
    ProfilePreferenceResponse,
    ProfileResponse,
    ProfileSocialResponse,
    Release,
)

if TYPE_CHECKING:
    from ..client import AnixartClient


class ProfileEndpoints:
    """Self profile, public profile cards and profile-list operations."""

    def __init__(self, client: AnixartClient) -> None:
        self._client = client

    def get_info(self) -> ProfileInfoResponse:
        """``GET /profile/info`` — self state, §5.2.1 (S#168)."""

        return self._client._request_model(
            ProfileInfoResponse,
            "GET",
            "/profile/info",
            idempotent=True,
        )

    def get_my_preferences(self) -> ProfilePreferenceResponse:
        """``GET /profile/preference/my`` — self preferences, §5.2.2 (S#215)."""

        return self._client._request_model(
            ProfilePreferenceResponse,
            "GET",
            "/profile/preference/my",
            idempotent=True,
        )

    def get_profile(self, profile_id: int) -> ProfileResponse:
        """``GET /profile/{id}`` — public profile card, §5.2.1 (S#172)."""

        return self._client._request_model(
            ProfileResponse,
            "GET",
            f"/profile/{profile_id}",
            idempotent=True,
        )

    def get_social(self, profile_id: int) -> ProfileSocialResponse:
        """``GET /profile/social/{id}`` — §5.2.1 (S#171)."""

        return self._client._request_model(
            ProfileSocialResponse,
            "GET",
            f"/profile/social/{profile_id}",
            idempotent=True,
        )

    # -- profile lists / bookmarks ----------------------------------------

    def get_list(
        self,
        status: int | ProfileListStatus,
        page: int = 1,
        *,
        sort: int | None = None,
        filter_announce: int | None = None,
    ) -> PageableResponse[Release]:
        """``GET /profile/list/all/{status}/{page}`` — §5.2.8 (S#202).

        ``status`` uses the documented profile-list enum ``1..5`` (§7.2);
        unknown numeric values are tolerated by :class:`ProfileListStatus`.
        Accepted ``sort``/``filter_announce`` values are ``UNKNOWN`` (U-22).
        """

        return self._client._request_model(
            PageableResponse[Release],
            "GET",
            f"/profile/list/all/{int(status)}/{page}",
            params={"sort": sort, "filter_announce": filter_announce},
            idempotent=True,
        )

    def get_profile_list(
        self,
        profile_id: int,
        status: int | ProfileListStatus,
        page: int = 1,
        *,
        sort: int | None = None,
        filter_announce: int | None = None,
    ) -> PageableResponse[Release]:
        """``GET /profile/list/all/{p_id}/{status}/{page}`` — §5.2.8 (S#201)."""

        return self._client._request_model(
            PageableResponse[Release],
            "GET",
            f"/profile/list/all/{profile_id}/{int(status)}/{page}",
            params={"sort": sort, "filter_announce": filter_announce},
            idempotent=True,
        )

    def add_to_list(
        self, status: int | ProfileListStatus, release_id: int
    ) -> ProfileListResponse:
        """``GET /profile/list/add/{status}/{r_id}`` — mutation, §5.2.8 (S#200)."""

        return self._client._request_model(
            ProfileListResponse,
            "GET",
            f"/profile/list/add/{int(status)}/{release_id}",
            idempotent=False,
        )

    def remove_from_list(
        self, status: int | ProfileListStatus, release_id: int
    ) -> ProfileListResponse:
        """``GET /profile/list/delete/{status}/{r_id}`` — mutation, §5.2.8 (S#203)."""

        return self._client._request_model(
            ProfileListResponse,
            "GET",
            f"/profile/list/delete/{int(status)}/{release_id}",
            idempotent=False,
        )


__all__ = ["ProfileEndpoints"]
