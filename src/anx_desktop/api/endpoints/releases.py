"""Release, favorite and release-video endpoints.

Sources: ``docs/api.md`` §5.3 (release card, random, votes, favorites),
§5.4 (video) and the checklist rows 5/11 in §10.1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import (
    Badge,
    DeleteVoteReleaseResponse,
    FavoritesResponse,
    PageableResponse,
    ProfileListStatus,
    Release,
    ReleaseResponse,
    ReleaseStreamingPlatform,
    ReleaseVideo,
    ReleaseVideoCategoriesResponse,
    ReleaseVideosResponse,
    VoteReleaseResponse,
)

if TYPE_CHECKING:
    from ..client import AnixartClient


class ReleaseEndpoints:
    """Release cards, random cards, votes, favorites and release videos."""

    def __init__(self, client: AnixartClient) -> None:
        self._client = client

    # -- release card ------------------------------------------------------

    def get_release(self, release_id: int, *, extended_mode: bool | None = None) -> ReleaseResponse:
        """``GET /release/{r_id}`` — §5.3.1 (S#244)."""

        return self._client._request_model(
            ReleaseResponse,
            "GET",
            f"/release/{release_id}",
            params={"extended_mode": extended_mode},
            idempotent=True,
        )

    def get_random(self, *, extended_mode: bool | None = None) -> ReleaseResponse:
        """``GET /release/random`` — §5.3.1 (S#239)."""

        return self._client._request_model(
            ReleaseResponse,
            "GET",
            "/release/random",
            params={"extended_mode": extended_mode},
            idempotent=True,
        )

    def get_random_favorite(self, *, extended_mode: bool | None = None) -> ReleaseResponse:
        """``GET /release/random/favorite`` — §5.3.1 (S#240)."""

        return self._client._request_model(
            ReleaseResponse,
            "GET",
            "/release/random/favorite",
            params={"extended_mode": extended_mode},
            idempotent=True,
        )

    def get_random_collection(
        self, collection_id: int, *, extended_mode: bool | None = None
    ) -> ReleaseResponse:
        """``GET /release/collection/{id}/random`` — §5.3.1 (S#238)."""

        return self._client._request_model(
            ReleaseResponse,
            "GET",
            f"/release/collection/{collection_id}/random",
            params={"extended_mode": extended_mode},
            idempotent=True,
        )

    def get_random_profile_list(
        self,
        profile_id: int,
        status: int | ProfileListStatus,
        *,
        extended_mode: bool | None = None,
    ) -> ReleaseResponse:
        """``GET /release/random/profile/list/{p_id}/{status}`` — §5.3.1 (S#241)."""

        return self._client._request_model(
            ReleaseResponse,
            "GET",
            f"/release/random/profile/list/{profile_id}/{int(status)}",
            params={"extended_mode": extended_mode},
            idempotent=True,
        )

    def get_continue(self, release_id: int) -> ReleaseResponse:
        """``GET /release/{r_id}/continue`` — §5.3.1 (S#246)."""

        return self._client._request_model(
            ReleaseResponse,
            "GET",
            f"/release/{release_id}/continue",
            idempotent=True,
        )

    def get_badges(self, release_id: int, page: int = 1) -> PageableResponse[Badge]:
        """``GET /release/{r_id}/badges/{page}`` — §5.3.1 (S#245)."""

        return self._client._request_model(
            PageableResponse[Badge],
            "GET",
            f"/release/{release_id}/badges/{page}",
            idempotent=True,
        )

    def get_related(self, related_id: int, page: int = 1) -> PageableResponse[Release]:
        """``GET /related/{relatedId}/{page}`` — §5.3.3 (S#237).

        The client is documented as sending ``API-Version: v2``; the header is
        reproduced here from §3.2.
        """

        return self._client._request_model(
            PageableResponse[Release],
            "GET",
            f"/related/{related_id}/{page}",
            headers={"API-Version": "v2"},
            idempotent=True,
        )

    def get_streaming_platform(self, release_id: int) -> PageableResponse[ReleaseStreamingPlatform]:
        """``GET /release/streaming/platform/{releaseId}`` — public, §5.3.4 (S#257).

        The docs mark the response as paged even though the path has no
        ``{page}``; no page parameter is invented here.
        """

        return self._client._request_model(
            PageableResponse[ReleaseStreamingPlatform],
            "GET",
            f"/release/streaming/platform/{release_id}",
            authenticated=False,
            idempotent=True,
        )

    # -- votes -------------------------------------------------------------

    def vote(self, release_id: int, vote: int) -> VoteReleaseResponse:
        """``GET /release/vote/add/{r_id}/{vote}`` — §5.3.1 (S#242).

        Despite using ``GET`` this is a mutation (§3.1), so it is never
        retried.  The docs only say the numeric vote values are likely
        ``-1/0/1`` (§7.4); the value is passed through unchanged.
        """

        return self._client._request_model(
            VoteReleaseResponse,
            "GET",
            f"/release/vote/add/{release_id}/{vote}",
            idempotent=False,
        )

    def delete_vote(self, release_id: int) -> DeleteVoteReleaseResponse:
        """``GET /release/vote/delete/{r_id}`` — mutation, §5.3.1 (S#243)."""

        return self._client._request_model(
            DeleteVoteReleaseResponse,
            "GET",
            f"/release/vote/delete/{release_id}",
            idempotent=False,
        )

    # -- release favorites -------------------------------------------------

    def add_favorite(self, release_id: int) -> FavoritesResponse:
        """``GET /favorite/add/{r_id}`` — mutation, §5.3.5 (S#121)."""

        return self._client._request_model(
            FavoritesResponse,
            "GET",
            f"/favorite/add/{release_id}",
            idempotent=False,
        )

    def get_favorites(
        self,
        page: int = 1,
        *,
        sort: int | None = None,
        filter_announce: int | None = None,
    ) -> PageableResponse[Release]:
        """``GET /favorite/all/{page}`` — §5.3.5 (S#122)."""

        return self._client._request_model(
            PageableResponse[Release],
            "GET",
            f"/favorite/all/{page}",
            params={"sort": sort, "filter_announce": filter_announce},
            idempotent=True,
        )

    def delete_favorite(self, release_id: int) -> FavoritesResponse:
        """``GET /favorite/delete/{r_id}`` — mutation, §5.3.5 (S#123)."""

        return self._client._request_model(
            FavoritesResponse,
            "GET",
            f"/favorite/delete/{release_id}",
            idempotent=False,
        )

    # -- release videos ----------------------------------------------------

    def get_release_video_categories(self) -> ReleaseVideoCategoriesResponse:
        """``GET /video/release/categories`` — public, §5.4.1 (S#259).

        .. warning::
           **Not implemented by contract.**  ``docs/api.md`` §6.12 marks the
           payload fields of ``ReleaseVideoCategoriesResponse`` as ``UNKNOWN``.

        TODO(task 06): capture the response and model its categories.
        """

        raise NotImplementedError(
            "docs/api.md §6.12 marks ReleaseVideoCategoriesResponse fields as UNKNOWN; "
            "returning only code would discard the category payload. "
            "TODO(task 06): capture and model it."
        )

    def get_release_videos_main(self, release_id: int) -> ReleaseVideosResponse:
        """``GET /video/release/{releaseId}`` — public, §5.4.1 (S#260).

        .. warning::
           **Not implemented by contract.**  ``docs/api.md`` §6.12 marks the
           payload fields of ``ReleaseVideosResponse`` as ``UNKNOWN``.

        TODO(task 06): capture the response and model its blocks.
        """

        raise NotImplementedError(
            "docs/api.md §6.12 marks ReleaseVideosResponse fields as UNKNOWN; "
            "returning only code would discard the video payload. "
            "TODO(task 06): capture and model it."
        )

    def get_release_videos(
        self, release_id: int, page: int = 1
    ) -> PageableResponse[ReleaseVideo]:
        """``GET /video/release/{releaseId}/{page}`` — public, §5.4.1 (S#262)."""

        return self._client._request_model(
            PageableResponse[ReleaseVideo],
            "GET",
            f"/video/release/{release_id}/{page}",
            authenticated=False,
            idempotent=True,
        )

    def get_release_videos_by_category(
        self, release_id: int, category_id: int, page: int = 1
    ) -> PageableResponse[ReleaseVideo]:
        """``GET /video/release/{releaseId}/category/{categoryId}/{page}`` — §5.4.1 (S#261)."""

        return self._client._request_model(
            PageableResponse[ReleaseVideo],
            "GET",
            f"/video/release/{release_id}/category/{category_id}/{page}",
            authenticated=False,
            idempotent=True,
        )

    def get_profile_videos(
        self, profile_id: int, page: int = 1
    ) -> PageableResponse[ReleaseVideo]:
        """``GET /video/profile/{p_id}/{page}`` — §5.4.1 (S#258)."""

        return self._client._request_model(
            PageableResponse[ReleaseVideo],
            "GET",
            f"/video/profile/{profile_id}/{page}",
            idempotent=True,
        )

    def add_video_favorite(self, release_id: int) -> FavoritesResponse:
        """``GET /releaseVideoFavorite/add/{r_id}`` — mutation, §5.4.2 (S#267)."""

        return self._client._request_model(
            FavoritesResponse,
            "GET",
            f"/releaseVideoFavorite/add/{release_id}",
            idempotent=False,
        )

    def get_video_favorites(
        self, profile_id: int, page: int = 1
    ) -> PageableResponse[ReleaseVideo]:
        """``GET /releaseVideoFavorite/all/{p_id}/{page}`` — §5.4.2 (S#268)."""

        return self._client._request_model(
            PageableResponse[ReleaseVideo],
            "GET",
            f"/releaseVideoFavorite/all/{profile_id}/{page}",
            idempotent=True,
        )

    def delete_video_favorite(self, release_id: int) -> FavoritesResponse:
        """``GET /releaseVideoFavorite/delete/{r_id}`` — mutation, §5.4.2 (S#269)."""

        return self._client._request_model(
            FavoritesResponse,
            "GET",
            f"/releaseVideoFavorite/delete/{release_id}",
            idempotent=False,
        )


__all__ = ["ReleaseEndpoints"]
