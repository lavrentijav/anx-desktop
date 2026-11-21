import pytest
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QWidget

from anx_desktop.ui.data import DemoRepository
from anx_desktop.ui.shell import TopBar
from anx_desktop.ui.theme import ThemeManager
from anx_desktop.ui.widgets.common import make_icon_label
from anx_desktop.ui.widgets.grid import CardGrid


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication(["pytest", "-platform", "offscreen"])


@pytest.fixture
def theme(app):
    manager = ThemeManager(app)
    manager.set_mode("light")
    return manager


def test_existing_icon_and_palette_follow_theme(app, theme):
    label = make_icon_label("info", "text_primary")
    light = label.pixmap().toImage()
    theme.set_mode("dark")
    assert app.palette().color(QPalette.ColorRole.Window) == theme.qcolor("background")
    assert label.pixmap().toImage() != light
    theme.set_mode("light")
    assert label.pixmap().toImage() == light


def test_topbar_refresh_respects_width(app, theme):
    bar = TopBar(DemoRepository())
    bar.resize(1000, bar.height())
    bar.show()
    app.processEvents()
    bar.set_header("Title", "Subtitle")
    bar.refresh_continue(True)
    assert bar._subtitle.isHidden()
    assert bar._continue.isHidden()
    bar.resize(1500, bar.height())
    assert not bar._subtitle.isHidden()
    assert not bar._continue.isHidden()
    bar.refresh_continue(False)
    assert bar._continue.isHidden()
    bar.close()


def test_grid_reflows_without_old_column_stretch(app, theme):
    cards = [QWidget() for _ in range(6)]
    for card in cards:
        card.setFixedSize(180, 40)
    grid = CardGrid(cards, min_card_width=130)
    margins = grid.layout().contentsMargins()
    padding = margins.left() + margins.right()
    gap = grid.layout().horizontalSpacing()
    grid.resize(padding + 3 * 180 + 2 * gap, 400)
    grid.show()
    app.processEvents()
    assert grid.layout().getItemPosition(2)[:2] == (0, 2)
    assert grid.minimumSizeHint().width() == padding + 180
    grid.resize(padding + 2 * 180 + gap - 1, 400)
    app.processEvents()
    assert grid.layout().getItemPosition(2)[:2] == (2, 0)
    assert grid.layout().columnStretch(2) == 0
    assert all(card.parentWidget() is grid for card in cards)
    grid.close()
