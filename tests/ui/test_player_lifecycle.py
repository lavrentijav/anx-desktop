"""Offline playback integration test; requires ffmpeg on PATH."""

import shutil
import subprocess
import time
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from anx_desktop.ui.data import Episode
from anx_desktop.ui.screens.base import ScreenContext
from anx_desktop.ui.screens.player import PlayerScreen, QtMediaBackend
from anx_desktop.ui.theme import ThemeManager


def wait_until(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < deadline, "Timed out waiting for Qt playback"
        QTest.qWait(20)


@pytest.mark.parametrize("upscale_mode", ["off", "auto", "cpu"])
def test_local_video_survives_reload_and_stops_on_hide(tmp_path, monkeypatch, upscale_mode):
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("ffmpeg is required to generate the local test clip")
    video = tmp_path / "local clip.mp4"
    subprocess.run(
        [ffmpeg, "-v", "error", "-f", "lavfi", "-i", "color=red:s=160x90:r=25",
         "-t", "4", "-c:v", "mpeg4", str(video)],
        check=True, timeout=15,
    )
    monkeypatch.delenv("ANX_UI_SMOKE_TEST", raising=False)
    app = QApplication.instance() or QApplication(["pytest", "-platform", "offscreen"])
    theme = ThemeManager(app)
    episode = Episode(42, 2, "Local clip", 4, False, False, "", "", 0,
                      QUrl.fromLocalFile(str(video)).toString())
    repo = SimpleNamespace(fetch_episodes=lambda *args, **kwargs: (episode,))
    errors = []
    host = SimpleNamespace(go_back=lambda: None, set_header=lambda *args: None, show_snackbar=errors.append)
    settings = SimpleNamespace(player_volume=70, audio_compressor=False, quality="720p", seek_seconds=10, upscale_mode=upscale_mode,
                               upscale_model="M", upscale_passes=2, upscale_scale=3, upscale_sharp=True)
    screen = PlayerScreen(ScreenContext(repo, theme, host, settings),
                          {"episode_id": episode.id, "episode_number": episode.number})
    screen.resize(900, 500)
    screen.show()
    screen.activate()
    try:
        wait_until(lambda: isinstance(screen._backend, QtMediaBackend))
        first = screen._backend
        sink = first._player.videoSink()
        wait_until(lambda: sink.videoFrame().isValid() and first.position() > 0)
        assert first.duration() == pytest.approx(4, abs=0.1)
        first.pause()
        slider = screen._position_slider
        assert slider.isVisible()
        QTest.mouseClick(slider, Qt.MouseButton.LeftButton, pos=slider.rect().center())
        wait_until(lambda: first.position() == pytest.approx(2, abs=0.1))
        assert not first.is_playing()

        screen.reload()
        assert screen._backend is None
        assert first._player.source().isEmpty()
        assert not first.is_playing()
        wait_until(lambda: isinstance(screen._backend, QtMediaBackend))
        second = screen._backend
        wait_until(lambda: second.position() > 0)
        assert second is not first
        assert len(screen._shortcuts) == 10

        screen.hide()
        assert screen._backend is None
        assert second._player.source().isEmpty()
        assert not second._retry_timer.isActive()
        assert not screen._hide_timer.isActive()
        assert not screen._stage_timer.isActive()
        screen.show()
        wait_until(lambda: isinstance(screen._backend, QtMediaBackend))
        wait_until(lambda: screen._backend.position() > 0)
        assert not errors

        screen.payload["episode_id"] = 999
        assert screen._resolve_stream() is None
    finally:
        screen.close()
        screen.deleteLater()
        QTest.qWait(0)
