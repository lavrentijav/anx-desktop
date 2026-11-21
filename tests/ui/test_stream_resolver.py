"""Unit tests for the Kodik iframe -> HLS resolver (no network)."""

from __future__ import annotations

import base64
import json

import httpx

from anx_desktop.ui.stream_resolver import resolve_iframe_stream


def _rot18_back(char: str) -> str:
    if "a" <= char <= "z":
        return chr((ord(char) - ord("a") - 18) % 26 + ord("a"))
    if "A" <= char <= "Z":
        return chr((ord(char) - ord("A") - 18) % 26 + ord("A"))
    return char


def _encode_src(src: str) -> str:
    encoded = base64.b64encode(src.encode("utf-8")).decode("ascii")
    return "".join(_rot18_back(char) for char in encoded)


PAGE = """
<html><body>
<script>
  var domain = "kodikplayer.com";
  var d_sign = "sign-d:123";
  var pd = "kodikplayer.com";
  var pd_sign = "sign-pd:123";
  var ref = "";
  var ref_sign = "sign-ref:123";
  var vInfo = {};
  vInfo.type = 'seria';
  vInfo.hash = 'hash-1';
  vInfo.id = '42';
</script>
</body></html>
"""

PLAYER_URL = "https://kodikplayer.com/seria/42/hash-1/720p"


def _links(qualities: dict[str, str]) -> dict:
    return {
        "links": {
            quality: [{"src": _encode_src(src)}] for quality, src in qualities.items()
        }
    }


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


def test_resolves_highest_available_quality():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, text=PAGE)
        seen.update(dict(httpx.QueryParams(request.content.decode())))
        body = _links(
            {
                "360": "//cdn.example/360.m3u8",
                "720": "//cdn.example/720.m3u8",
            }
        )
        return httpx.Response(200, json=body)

    result = resolve_iframe_stream(PLAYER_URL, quality="1080p", client=_client(handler))

    assert result is not None
    assert result.quality == "720"
    assert result.url == "https://cdn.example/720.m3u8"
    assert seen["type"] == "seria"
    assert seen["hash"] == "hash-1"
    assert seen["id"] == "42"
    assert seen["d_sign"] == "sign-d:123"


def test_requested_quality_is_preferred():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, text=PAGE)
        body = _links(
            {
                "360": "//cdn.example/360.m3u8",
                "720": "//cdn.example/720.m3u8",
            }
        )
        return httpx.Response(200, json=body)

    result = resolve_iframe_stream(PLAYER_URL, quality="360p", client=_client(handler))

    assert result is not None
    assert result.quality == "360"
    assert result.url == "https://cdn.example/360.m3u8"


def test_missing_player_fields_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>no player variables</html>")

    assert resolve_iframe_stream(PLAYER_URL, client=_client(handler)) is None


def test_error_response_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, text=PAGE)
        return httpx.Response(500, text="boom")

    assert resolve_iframe_stream(PLAYER_URL, client=_client(handler)) is None


def test_broken_links_payload_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, text=PAGE)
        return httpx.Response(200, json={"links": {"720": []}})

    assert resolve_iframe_stream(PLAYER_URL, client=_client(handler)) is None


def test_plain_src_is_kept_and_payload_matches_player_page():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, text=PAGE)
        body = {"links": {"720": [{"src": "https://cdn.example/direct.mp4"}]}}
        return httpx.Response(200, text=json.dumps(body))

    result = resolve_iframe_stream(PLAYER_URL, client=_client(handler))

    assert result is not None
    assert result.url == "https://cdn.example/direct.mp4"


def test_quality_choices_include_only_playable_source_variants():
    from anx_desktop.ui.stream_resolver import _best_stream

    raw = json.dumps({"links": {
        "480": [{"src": "https://example.test/480.m3u8"}],
        "720p": [{"src": "//example.test/720.m3u8"}],
        "2160": [{"src": ""}],
    }})
    actual = _best_stream(raw, "2160p")
    assert actual is not None
    assert actual.available_qualities == ("480", "720")
    assert actual.quality == "720"
    assert actual.url == "https://example.test/720.m3u8"
    assert _best_stream(raw, "480p").quality == "480"
