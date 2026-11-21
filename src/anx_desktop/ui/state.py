"""In-memory UI preferences shared by the shell and screens.

A small subset is connected to real behaviour (theme, view mode, demo state,
compact sidebar, player defaults).  Persistence to disk is deliberately left
out of the clean-room scaffold.
"""

from __future__ import annotations

from dataclasses import dataclass

from .data import DemoState


@dataclass
class AppSettings:
    theme_mode: str = "system"
    view_mode: str = "grid"  # grid | list
    compact_sidebar: bool = False
    continue_watching: bool = True
    home_tab: str = "home_0"
    bookmarks_tab: str = "bookmark_0"
    notification_filter: str = "all"
    demo_state: DemoState = DemoState.DATA
    player: str = "ask"
    quality: str = "1080p"
    upscale_mode: str = "off"
    upscale_model: str = "S"
    upscale_passes: int = 1
    upscale_scale: float = 2
    upscale_sharp: bool = False
    audio_compressor: bool = False
    player_volume: int = 70
    seek_seconds: int = 10
    autoplay: bool = True
    remember_source: bool = True
    horizontal_only: bool = False
    hide_channel_widgets: bool = False
    time_format: str = "hours"
    economy_mode: bool = False
    alternative_connection: bool = False
    image_cache_limit_mb: int = 512
    image_cache_used_mb: int = 186
    reduce_motion: bool = False
    push_episodes: bool = True
    push_releases: bool = True
    push_articles: bool = True
    push_comments: bool = True
    push_reports: bool = True
    profile_pinned_section: str = "Статистика"
    pinned_section: str = "Статистика"
    selected_badge_id: int = 7000
