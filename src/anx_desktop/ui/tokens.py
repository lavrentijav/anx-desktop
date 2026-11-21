"""Typed access to the canonical 8.5.2 design tokens.

`ui/resources/ui-8.5-tokens.json` is the only source of colours, spacings, radii and
sizes in the UI.  No widget is allowed to hardcode a hex value or a component
size: everything goes through :class:`Tokens` and :class:`ThemeManager`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


class TokenError(RuntimeError):
    """Raised when the canonical token document cannot be found or parsed."""


_TOKEN_PATH = Path(__file__).resolve().parent / "resources" / "ui-8.5-tokens.json"


class Tokens:
    """Read-only wrapper around the token JSON."""

    def __init__(self, data: Mapping[str, Any], source: Path | None = None) -> None:
        self._data = dict(data)
        self.source = source

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Tokens":
        candidates = [Path(path)] if path else [_TOKEN_PATH]
        for candidate in candidates:
            try:
                with candidate.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                return cls(data, candidate)
            except FileNotFoundError:
                continue
            except (OSError, json.JSONDecodeError) as exc:
                raise TokenError(f"Не удалось прочитать токены {candidate}: {exc}") from exc
        checked = ", ".join(str(item) for item in candidates)
        raise TokenError(
            "Не найден ui/resources/ui-8.5-tokens.json. Проверьте пути: " + checked
        )

    # ------------------------------------------------------------------ meta
    @property
    def raw(self) -> Mapping[str, Any]:
        return self._data

    @property
    def app_label(self) -> str:
        return str(self._data.get("meta", {}).get("app_label", "anx-desktop"))

    # ---------------------------------------------------------------- colours
    def color_set(self, theme: str) -> Mapping[str, str]:
        theme_key = "dark" if theme == "dark" else "light"
        return self._data["colors"][theme_key]

    def color(self, role: str, theme: str = "light") -> str:
        colors = self.color_set(theme)
        if role not in colors:
            raise KeyError(f"Нет цветового токена {role!r} для темы {theme!r}")
        return str(colors[role])

    # ------------------------------------------------------------- typography
    def typography(self, scale_name: str) -> Mapping[str, Any]:
        try:
            return self._data["typography"]["scale"][scale_name]
        except KeyError as exc:
            raise KeyError(f"Нет типографического токена {scale_name!r}") from exc

    def font_family(self, family_key: str = "default") -> str:
        return str(self._data["typography"]["font_families"].get(family_key, "Roboto"))

    # ---------------------------------------------------------------- spacing
    def space(self, name: str) -> float:
        return float(self._data["spacing"]["scale_dp"][name])

    def semantic(self, name: str) -> float:
        semantic = self._data["spacing"]["semantic_dp"]
        if name in semantic:
            return float(semantic[name])
        # A few component sizes live in layout (e.g. list_avatar_size_dp).
        layout_key = f"{name}_dp"
        if layout_key in self._data["layout"]:
            return float(self._data["layout"][layout_key])
        raise KeyError(f"Нет размерного токена {name!r}")

    def radius(self, name: str) -> float:
        return float(self._data["radii"][name])

    # ----------------------------------------------------------------- layout
    def layout(self, name: str) -> Any:
        return self._data["layout"][name]

    def desktop(self, name: str) -> int:
        return int(self._data["layout"]["desktop_mapping_proposal"][name])

    # ------------------------------------------------------------- dimensions
    def list_poster_size(self) -> tuple[int, int]:
        return (
            int(self._data["layout"]["list_poster_width_dp"]),
            int(self._data["layout"]["list_poster_height_dp"]),
        )

    def compact_poster_size(self) -> tuple[int, int]:
        return (
            int(self._data["layout"]["compact_poster_width_dp"]),
            int(self._data["layout"]["compact_poster_height_dp"]),
        )

    def grid_poster_size(self) -> tuple[int, int]:
        height = int(self._data["layout"]["grid_item_poster_height_dp"])
        # 8.5.2 grid postcards are 3:4 (see layout.grid_posters_visible_aspect).
        width = int(round(height * 3 / 4))
        return width, height


_TOKENS: Tokens | None = None


def tokens() -> Tokens:
    """Process-wide token store (loaded lazily)."""

    global _TOKENS
    if _TOKENS is None:
        _TOKENS = Tokens.load()
    return _TOKENS
