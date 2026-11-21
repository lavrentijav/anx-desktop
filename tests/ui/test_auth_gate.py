from PySide6.QtWidgets import QApplication

from anx_desktop.ui.app import MainWindow
from anx_desktop.ui.data import DemoRepository
from anx_desktop.ui.shell import NAV_ENTRIES
from anx_desktop.ui.state import AppSettings
from anx_desktop.ui.theme import ThemeManager
from anx_desktop.ui.tokens import Tokens


def test_session_required_before_showing_catalog():
    class RepositoryStub:
        is_authenticated = False

        def __init__(self):
            self.data = DemoRepository()

        def __getattr__(self, name):
            if name == "subscribe_state":
                raise AttributeError(name)
            assert self.is_authenticated, f"Repository called before login: {name}"
            return getattr(self.data, name)

    app = QApplication.instance() or QApplication(["pytest", "-platform", "offscreen"])
    repo = RepositoryStub()
    tokens = Tokens.load()
    theme = ThemeManager(app, tokens)
    window = MainWindow(repo, theme, AppSettings(), tokens)
    try:
        assert window._current_route == "auth_email"
        assert window.sidebar.isHidden() and window.topbar.isHidden()
        window.navigate("discover")
        assert window._current_route == "auth_email"

        repo.is_authenticated = True
        window.navigate("home")
        assert window._current_route == "home"
        assert not window.sidebar.isHidden() and not window.topbar.isHidden()
        window.navigate("discover")
        assert window._back

        repo.is_authenticated = False
        window.navigate("auth")
        window.go_back()
        window.go_forward()
        assert window._current_route == "auth_email"
        assert window.sidebar.isHidden() and window.topbar.isHidden()
        assert not window._back and not window._forward
    finally:
        window.close()


def test_sidebar_does_not_list_auxiliary_screens():
    routes = {entry.route for entry in NAV_ENTRIES}
    assert routes.isdisjoint({"auth", "auth_email", "need_auth", "player", "deletion", "health", "badges"})


def test_episodes_remain_visible_when_channels_are_missing():
    class NoChannelsRepository(DemoRepository):
        def fetch_channels(self, *args, **kwargs):
            return ()

    app = QApplication.instance() or QApplication(["pytest", "-platform", "offscreen"])
    tokens = Tokens.load()
    window = MainWindow(NoChannelsRepository(), ThemeManager(app, tokens), AppSettings(), tokens)
    try:
        window.navigate("episodes", 1000)
        screen = window._current_screen
        screen.populate()
        assert screen._episodes
        assert screen._list_layout.count() > 0
    finally:
        window.close()
