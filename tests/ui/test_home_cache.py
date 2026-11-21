from dataclasses import replace
from threading import Event

import pytest
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication

from anx_desktop.ui.data import Page, Release, TabSpec
from anx_desktop.ui.home_cache import HomeCache
from anx_desktop.ui.screens.base import ScreenContext
from anx_desktop.ui.screens.home import PAGE_SIZE, HomeScreen
from anx_desktop.ui.state import AppSettings
from anx_desktop.ui.theme import ThemeManager


def catalog(title, *, personalized=False):
    release = Release(
        1, title, "Original", 2025, 8.0, 12, 10, "Description",
        genres=("Action",), screenshots=("image",), is_favorite=personalized,
        list_status=2 if personalized else 0,
    )
    return Page((release,), 1, PAGE_SIZE, 24, 2)


def test_persistent_cache_only_stores_public_first_pages(tmp_path):
    path = tmp_path / "home.sqlite3"
    cache = HomeCache(path)
    live = catalog("Каталог", personalized=True)
    cache.store("home_0", live)
    cache.store("custom", live)
    assert not path.exists()
    cache.store("home_1", live)
    cache.store("home_1", replace(live, items=(), total_count=0, total_pages=0))
    cache.store("home_1", replace(live, page=2))
    reopened = HomeCache(path)
    assert reopened.load("home_1", PAGE_SIZE) == catalog("Каталог")
    assert reopened.load("home_2", PAGE_SIZE) is None
    assert reopened.load("home_1", PAGE_SIZE + 1) is None
    assert b"is_favorite" not in path.read_bytes()
    assert b"list_status" not in path.read_bytes()


def test_corrupt_cache_is_a_miss(tmp_path):
    path = tmp_path / "home.sqlite3"
    path.write_text("not SQLite")
    cache = HomeCache(path)
    assert cache.load("home_1", PAGE_SIZE) is None
    cache.store("home_1", catalog("Live"))  # best effort, no exception


@pytest.mark.parametrize("outcome", ["fresh", "empty", "exception", "stale"])
def test_home_renders_cache_before_background_refresh(tmp_path, outcome):
    app = QApplication.instance() or QApplication(["pytest", "-platform", "offscreen"])
    theme = ThemeManager(app)
    cache = HomeCache(tmp_path / "home.sqlite3")
    cached = catalog("Cached")
    fresh = catalog("Fresh")
    other = catalog("Other tab")
    cache.store("home_1", cached)
    started = Event()
    unblock = Event()

    class Repo:
        def home_tabs(self):
            return (TabSpec(key="home_1", title="First"), TabSpec(key="home_2", title="Second"))

        def fetch_home(self, tab, page, page_size):
            if tab == "home_2":
                return other
            started.set()
            if not unblock.wait(3):
                raise TimeoutError("Test did not release the worker")
            if outcome == "exception":
                raise OSError("Offline")
            if outcome == "empty":
                return Page((), page, page_size, 0, 0)
            return fresh

    screen = HomeScreen(ScreenContext(Repo(), theme, None, AppSettings(home_tab="home_1")))
    screen._cache = cache
    try:
        screen.reload()
        assert started.wait(2)
        assert screen.stack.currentWidget() is screen.scroll
        assert screen._shown_page == cached
        if outcome == "stale":
            screen._on_tab_changed("home_2")
        unblock.set()
        assert QThreadPool.globalInstance().waitForDone(3000)
        app.processEvents()
        assert not screen._fetching
        expected = fresh if outcome == "fresh" else cached
        assert screen._shown_page == (other if outcome == "stale" else expected)
        assert screen.stack.currentWidget() is screen.scroll
        assert cache.load("home_1", PAGE_SIZE) == expected
    finally:
        unblock.set()
        QThreadPool.globalInstance().waitForDone(3000)
        screen.deleteLater()
