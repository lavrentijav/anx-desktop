"""Release comments — ``docs/api.md`` §5.3.2 (checklist row 8)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import (
    CommentAddRequest,
    CommentAddResponse,
    CommentDeleteResponse,
    CommentEditRequest,
    CommentEditResponse,
    CommentProcessRequest,
    PageableResponse,
    Profile,
    ReleaseComment,
    Response,
)

if TYPE_CHECKING:
    from ..client import AnixartClient


class CommentEndpoints:
    """All ten documented release-comment operations."""

    def __init__(self, client: AnixartClient) -> None:
        self._client = client

    def get_comments(
        self,
        release_id: int,
        page: int = 1,
        *,
        sort: int | None = None,
    ) -> PageableResponse[ReleaseComment]:
        """``GET /release/comment/all/{releaseId}/{page}`` — §5.3.2 (S#249)."""

        return self._client._request_model(
            PageableResponse[ReleaseComment],
            "GET",
            f"/release/comment/all/{release_id}/{page}",
            params={"sort": sort},
            idempotent=True,
        )

    def get_profile_comments(
        self,
        profile_id: int,
        page: int = 1,
        *,
        sort: int | None = None,
    ) -> PageableResponse[ReleaseComment]:
        """``GET /release/comment/all/profile/{p_id}/{page}`` — §5.3.2 (S#248)."""

        return self._client._request_model(
            PageableResponse[ReleaseComment],
            "GET",
            f"/release/comment/all/profile/{profile_id}/{page}",
            params={"sort": sort},
            idempotent=True,
        )

    def add_comment(
        self,
        release_id: int,
        *,
        message: str,
        parent_comment_id: int | None = None,
        reply_to_profile_id: int | None = None,
        spoiler: bool = False,
    ) -> CommentAddResponse[ReleaseComment]:
        """``POST /release/comment/add/{releaseId}`` — §5.3.2 (S#247).

        ``CommentAddRequest`` uses camelCase wire names (§6.7):
        ``parentCommentId``, ``replyToProfileId`` and ``spoiler``.
        """

        request = CommentAddRequest.model_validate(
            {
                "message": message,
                "parentCommentId": parent_comment_id,
                "replyToProfileId": reply_to_profile_id,
                "spoiler": spoiler,
            }
        )
        return self._client._request_model(
            CommentAddResponse[ReleaseComment],
            "POST",
            f"/release/comment/add/{release_id}",
            json_body=request.model_dump(by_alias=True, exclude_none=True),
            idempotent=False,
        )

    def get_comment(self, release_id: int) -> ReleaseComment:
        """``GET /release/comment/{releaseId}`` — §5.3.2 (S#256).

        The path parameter is named ``releaseId`` in the docs and the response
        is a single ``ReleaseComment``.  The server semantics are reproduced
        literally.
        """

        return self._client._request_model(
            ReleaseComment,
            "GET",
            f"/release/comment/{release_id}",
            idempotent=True,
        )

    def delete_comment(self, comment_id: int) -> CommentDeleteResponse:
        """``GET /release/comment/delete/{commentId}`` — mutation, §5.3.2 (S#250)."""

        return self._client._request_model(
            CommentDeleteResponse,
            "GET",
            f"/release/comment/delete/{comment_id}",
            idempotent=False,
        )

    def edit_comment(
        self, comment_id: int, request: CommentEditRequest
    ) -> CommentEditResponse:
        """``POST /release/comment/edit/{commentId}`` — §5.3.2 (S#251)."""

        return self._client._request_model(
            CommentEditResponse,
            "POST",
            f"/release/comment/edit/{comment_id}",
            json_body=request.model_dump(by_alias=True, exclude_none=True),
            idempotent=False,
        )

    def process_comment(
        self, comment_id: int, request: CommentProcessRequest
    ) -> Response:
        """``POST /release/comment/process/{commentId}`` — moderation, §5.3.2 (S#252)."""

        return self._client._request_model(
            Response,
            "POST",
            f"/release/comment/process/{comment_id}",
            json_body=request.model_dump(by_alias=True, exclude_none=True),
            idempotent=False,
        )

    def get_replies(
        self,
        comment_id: int,
        page: int = 1,
        *,
        sort: int | None = None,
    ) -> PageableResponse[ReleaseComment]:
        """``POST /release/comment/replies/{commentId}/{page}`` — §5.3.2 (S#253).

        Read-only despite using POST; retries are safe.
        """

        return self._client._request_model(
            PageableResponse[ReleaseComment],
            "POST",
            f"/release/comment/replies/{comment_id}/{page}",
            params={"sort": sort},
            idempotent=True,
        )

    def vote_comment(self, comment_id: int, vote: int) -> Response:
        """``GET /release/comment/vote/{commentId}/{vote}`` — mutation, §5.3.2 (S#254).

        The docs only say the vote values are likely ``-1/0/1`` (§7.4); the
        value is passed through unchanged.
        """

        return self._client._request_model(
            Response,
            "GET",
            f"/release/comment/vote/{comment_id}/{vote}",
            idempotent=False,
        )

    def get_votes(
        self,
        comment_id: int,
        page: int = 1,
        *,
        sort: int | None = None,
    ) -> PageableResponse[Profile]:
        """``GET /release/comment/votes/{commentId}/{page}`` — §5.3.2 (S#255)."""

        return self._client._request_model(
            PageableResponse[Profile],
            "GET",
            f"/release/comment/votes/{comment_id}/{page}",
            params={"sort": sort},
            idempotent=True,
        )


__all__ = ["CommentEndpoints"]
