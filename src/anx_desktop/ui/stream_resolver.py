"""Resolve third-party iframe players to a direct HLS manifest.

QtWebEngine bundled with PySide6 is built without proprietary codecs, so the
Kodik player can render its UI but cannot decode H.264/AAC video. Kodik's page
loads stream links from its own ``/ftor`` endpoint; this module repeats that
request (same page variables the player uses) and returns an HLS manifest for
``QMediaPlayer``, whose FFmpeg backend has the system codecs.

Only Kodik-style player URLs (``/seria/...``, ``/serial/...``, ``/movie/...``)
are supported. Any failure returns ``None`` so the caller can fall back to the
embedded web player.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

DEFAULT_TIMEOUT = 12.0
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36"
)


@dataclass(frozen=True)
class ResolvedStream:
    url: str
    quality: str
    available_qualities: tuple[str, ...] = ()


def resolve_iframe_stream(
    page_url: str,
    *,
    quality: str = "1080p",
    timeout: float = DEFAULT_TIMEOUT,
    client: httpx.Client | None = None,
) -> ResolvedStream | None:
    """Return the best direct stream for a Kodik player URL, or ``None``."""

    if not page_url:
        return None
    split = urlsplit(page_url)
    if split.scheme not in {"http", "https"} or not split.netloc:
        return None
    own_client = client is None
    http = client or httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
    )
    try:
        page = http.get(page_url, headers={"Referer": page_url})
        if page.status_code >= 400:
            return None
        fields = _page_fields(page.text)
        if fields is None:
            return None
        response = http.post(
            f"{split.scheme}://{split.netloc}/ftor",
            data=_ftor_payload(fields),
            headers={
                "Referer": page_url,
                "Origin": f"{split.scheme}://{split.netloc}",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        if response.status_code >= 400:
            return None
        return _best_stream(response.text, quality)
    except (httpx.HTTPError, ValueError, OSError):
        return None
    finally:
        if own_client:
            http.close()


def _string_field(html: str, name: str) -> str | None:
    match = re.search(
        rf"var\s+{re.escape(name)}\s*=\s*\"((?:[^\"\\]|\\.)*)\"\s*;",
        html,
    )
    if match is None:
        return None
    return match.group(1).replace('\\"', '"').replace("\\\\", "\\")


def _v_info_field(html: str, name: str) -> str | None:
    match = re.search(
        rf"vInfo\.{re.escape(name)}\s*=\s*'((?:[^'\\]|\\.)*)'\s*;",
        html,
    )
    return match.group(1).replace("\\'", "'") if match else None


def _page_fields(html: str) -> dict[str, str] | None:
    fields: dict[str, str] = {}
    for name in ("domain", "d_sign", "pd", "pd_sign", "ref", "ref_sign"):
        value = _string_field(html, name)
        if value is not None:
            fields[name] = value
    for source, target in (("type", "type"), ("hash", "hash"), ("id", "id")):
        value = _v_info_field(html, source)
        if value is not None:
            fields[target] = value
    if not {"d_sign", "ref_sign", "hash", "id"}.issubset(fields):
        return None
    return fields


def _ftor_payload(fields: Mapping[str, str]) -> dict[str, str]:
    payload = {
        "d": fields.get("domain", ""),
        "d_sign": fields.get("d_sign", ""),
        "pd": fields.get("pd", ""),
        "pd_sign": fields.get("pd_sign", ""),
        "ref": fields.get("ref", ""),
        "ref_sign": fields.get("ref_sign", ""),
        "cdn_is_working": "false",
        "type": fields.get("type", ""),
        "hash": fields.get("hash", ""),
        "id": fields.get("id", ""),
    }
    return {key: value for key, value in payload.items() if value}


def _best_stream(raw: str, quality: str) -> ResolvedStream | None:
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    links = data.get("links") if isinstance(data, dict) else None
    if not isinstance(links, dict):
        return None
    available: dict[str, str] = {}
    for key, items in links.items():
        label = _normalize_quality(key)
        if not label or label in available:
            continue
        for item in _as_items(items):
            url = _decoded_src(item.get("src"))
            if url.startswith("//"):
                url = "https:" + url
            if url.startswith(("https://", "http://")):
                available[label] = url
                break
    if not available:
        return None
    qualities = tuple(sorted(available, key=_quality_key))
    wanted = _normalize_quality(quality)
    chosen = wanted if wanted in available else qualities[-1]
    return ResolvedStream(available[chosen], chosen, qualities)


def _as_items(value: object) -> Iterable[dict]:
    if isinstance(value, dict):
        return (value,)
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, dict))
    return ()


def _normalize_quality(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits or ""


def _quality_key(value: str) -> int:
    try:
        return int(_normalize_quality(value) or 0)
    except ValueError:
        return 0


def _decoded_src(src: object) -> str:
    if not isinstance(src, str) or not src:
        return ""
    if "//" in src:
        return src
    shifted = "".join(_rot18(char) for char in src)
    padded = shifted + "=" * (-len(shifted) % 4)
    try:
        decoded = base64.b64decode(padded, validate=False).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return ""
    if decoded.startswith("//"):
        return "https:" + decoded
    return decoded


def _rot18(char: str) -> str:
    if "a" <= char <= "z":
        return chr((ord(char) - ord("a") + 18) % 26 + ord("a"))
    if "A" <= char <= "Z":
        return chr((ord(char) - ord("A") + 18) % 26 + ord("A"))
    return char
