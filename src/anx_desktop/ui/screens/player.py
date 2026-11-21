"""Плеер: controls, timeline, volume, fullscreen and hotkeys.

Direct media is played through QtMultimedia; the demo uses a simulated backend.
"""

from __future__ import annotations

import os
from html import escape as _escape_html

from PySide6.QtCore import QEvent, QObject, QRectF, QSizeF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSlider,
    QStackedLayout,
    QStyle,
    QStyleOptionSlider,
    QVBoxLayout,
    QWidget,
)

from .. import icons
from ..data import DemoRepository
from ..formatting import format_timestamp
from ..strings import S
from ..stream_resolver import resolve_iframe_stream
from ..theme import active_theme
from ..widgets import IconButton
from ..widgets.empty_state import Spinner
from .base import BaseScreen


def _iframe_embed_html(url: str) -> str:
    """Wrap a player URL into a local page embedding it in an iframe.

    Kodik and similar hosts check ``window.top !== window.self`` and refuse to
    play when opened as a top-level document; a local wrapper restores the
    original app's behaviour.
    """

    src = _escape_html(url, quote=True)
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        "<style>html,body{margin:0;width:100%;height:100%;background:#000;overflow:hidden}"
        "iframe{position:absolute;top:0;left:0;width:100%;height:100%;border:0}"
        "</style></head><body>"
        f'<iframe src="{src}" allow="autoplay; fullscreen; encrypted-media; picture-in-picture"'
        ' allowfullscreen></iframe>'
        "</body></html>"
    )


class StubPlayerBackend(QObject):
    """Simulated media backend. TODO(player): replace with a real engine."""

    position_changed = Signal(float)
    duration_changed = Signal(float)
    playing_changed = Signal(bool)
    buffering_changed = Signal(bool)
    error_occurred = Signal(str)

    def __init__(self, duration: float = 23 * 60 + 40, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._duration = max(30.0, duration)
        self._position = 12.0
        self._playing = False
        self._buffering = True
        self._rate = 1.0
        self._volume = 70
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._tick)
        self._ready_timer = QTimer(self)
        self._ready_timer.setSingleShot(True)
        self._ready_timer.timeout.connect(self._ready)
        self._ready_timer.start(900)

    def _ready(self) -> None:
        self._buffering = False
        self.buffering_changed.emit(False)
        self.play()

    def duration(self) -> float:
        return self._duration

    def position(self) -> float:
        return self._position

    def is_playing(self) -> bool:
        return self._playing

    def play(self) -> None:
        if self._playing:
            return
        self._playing = True
        self._timer.start()
        self.playing_changed.emit(True)

    def pause(self) -> None:
        if not self._playing:
            return
        self._playing = False
        self._timer.stop()
        self.playing_changed.emit(False)

    def stop(self) -> None:
        self._ready_timer.stop()
        self.pause()

    def toggle(self) -> None:
        if self._playing:
            self.pause()
        else:
            self.play()

    def seek(self, position: float) -> None:
        self._position = max(0.0, min(self._duration, position))
        self.position_changed.emit(self._position)

    def seek_relative(self, delta: float) -> None:
        self.seek(self._position + delta)

    def set_rate(self, rate: float) -> None:
        self._rate = rate

    def set_volume(self, volume: int) -> None:
        self._volume = max(0, min(100, volume))

    def volume(self) -> int:
        return self._volume

    def _tick(self) -> None:
        if not self._playing:
            return
        self._position = min(self._duration, self._position + 0.25 * self._rate)
        self.position_changed.emit(self._position)
        if self._position >= self._duration:
            self.pause()


class QtMediaBackend(QObject):
    """Real playback for direct media URLs via QtMultimedia."""

    position_changed = Signal(float)
    duration_changed = Signal(float)
    playing_changed = Signal(bool)
    buffering_changed = Signal(bool)
    error_occurred = Signal(str)

    def __init__(self, url: str, video_output: QObject, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink

        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        from ..playback_audio import PlaybackAudio

        self.audio_effects = PlaybackAudio(self._player, self._audio)
        self.compressor = False
        self._volume = 70
        if isinstance(video_output, QVideoSink):
            self._player.setVideoSink(video_output)
        else:
            self._player.setVideoOutput(video_output)
        self._url = url
        self._retries = 0
        self._stopped = False
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self.start)
        self._player.positionChanged.connect(
            lambda ms: self.position_changed.emit(ms / 1000.0)
        )
        self._player.durationChanged.connect(
            lambda ms: self.duration_changed.emit(ms / 1000.0)
        )
        self._player.playbackStateChanged.connect(
            lambda state: self.playing_changed.emit(
                state == QMediaPlayer.PlaybackState.PlayingState
            )
        )
        self._player.mediaStatusChanged.connect(self._on_status)
        self._player.errorOccurred.connect(self._on_error)

    def start(self) -> None:
        if self._stopped:
            return
        self._player.setSource(QUrl())
        self._player.setSource(QUrl(self._url))
        self._player.play()

    def _on_error(self, error, message) -> None:
        from PySide6.QtMultimedia import QMediaPlayer

        # CDN TLS connections are occasionally dropped; retry the initial
        # open a few times before surfacing the error to the UI.
        retryable = error in (
            QMediaPlayer.Error.ResourceError,
            QMediaPlayer.Error.FormatError,
        )
        if self._stopped or self._retry_timer.isActive():
            return
        if retryable and self._retries < 3:
            self._retries += 1
            self._retry_timer.start(700 * self._retries)
            return
        self.error_occurred.emit(message)

    def _on_status(self, status) -> None:
        from PySide6.QtMultimedia import QMediaPlayer

        buffering = status in (
            QMediaPlayer.MediaStatus.LoadingMedia,
            QMediaPlayer.MediaStatus.BufferingMedia,
            QMediaPlayer.MediaStatus.StalledMedia,
        )
        self.buffering_changed.emit(buffering)

    def duration(self) -> float:
        return self._player.duration() / 1000.0

    def position(self) -> float:
        return self._player.position() / 1000.0

    def is_playing(self) -> bool:
        from PySide6.QtMultimedia import QMediaPlayer

        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._stopped = True
        self._retry_timer.stop()
        self.audio_effects.stop()
        self.audio_effects.close()
        self._player.setSource(QUrl())
        self._player.setVideoOutput(None)

    def toggle(self) -> None:
        if self.is_playing():
            self.pause()
        else:
            self.play()

    def seek(self, position: float) -> None:
        self.audio_effects.seek(int(max(0.0, position) * 1000))

    def seek_relative(self, delta: float) -> None:
        self.seek(self.position() + delta)

    def set_rate(self, rate: float) -> None:
        self._player.setPlaybackRate(rate)

    def set_volume(self, volume: int) -> None:
        self._volume = max(0, min(200, volume))
        self.audio_effects.configure(volume_percent=self._volume, compressor=self.compressor)

    def volume(self) -> int:
        return self._volume


class VideoSurface(QWidget):
    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), theme.qcolor("snackbar_background"))
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        painter.setPen(theme.qcolor("border_soft"))
        painter.setBrush(theme.qcolor("player_scrim"))
        radius = theme.radius("collection_card")
        painter.drawRoundedRect(rect, radius, radius)
        # Neutral clean-room backdrop; the actual picture is provided by the
        # future media backend (TODO(player)).
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(theme.qcolor("border_image"))
        cx, cy = rect.center().x(), rect.center().y()
        span = min(rect.width(), rect.height()) * 0.16
        painter.drawEllipse(rect.center(), span, span)
        painter.drawLine(int(cx - span), int(cy), int(cx + span), int(cy))


class VideoView(QGraphicsView):
    """Composited video surface (non-native, so controls can sit above it)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        from PySide6.QtMultimediaWidgets import QGraphicsVideoItem

        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setInteractive(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet("background-color: #000;")
        self._scene = QGraphicsScene(self)
        self._item = QGraphicsVideoItem()
        self._item.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self._scene.addItem(self._item)
        self.setScene(self._scene)

    @property
    def video_item(self):
        return self._item

    def _fit_item(self) -> None:
        size = self.viewport().size()
        self._scene.setSceneRect(0, 0, size.width(), size.height())
        self._item.setSize(QSizeF(size.width(), size.height()))

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._fit_item()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._fit_item()


class TimelineSlider(QSlider):
    seek_requested = Signal()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            option = QStyleOptionSlider()
            self.initStyleOption(option)
            style = self.style()
            control = QStyle.ComplexControl.CC_Slider
            handle = style.subControlRect(control, option, QStyle.SubControl.SC_SliderHandle, self)
            point = event.position().toPoint()
            if not handle.contains(point):
                groove = style.subControlRect(control, option, QStyle.SubControl.SC_SliderGroove, self)
                self.setValue(QStyle.sliderValueFromPosition(
                    self.minimum(), self.maximum(), point.x() - groove.x() - handle.width() // 2,
                    max(1, groove.width() - handle.width()), option.upsideDown,
                ))
                self.seek_requested.emit()
                event.accept()
                return
        super().mousePressEvent(event)


class PlayerScreen(BaseScreen):
    supports_empty = False

    def __init__(self, ctx, payload: dict | None = None) -> None:
        super().__init__(ctx, title=S.PLAYER_TITLE)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.payload = payload or {}
        self.release_id = int(self.payload.get("release_id", 1000))
        self.episode_title = str(self.payload.get("episode", S.PLAYER_DEFAULT_EPISODE))
        self.release_title = str(self.payload.get("title", S.PLAYER_DEFAULT_RELEASE))
        self._backend: StubPlayerBackend | QtMediaBackend | None = None
        self._iframe_source = False
        self._player_page: QWidget | None = None
        self._video_view: QWidget | None = None
        self._upscale_button: QPushButton | None = None
        self._quality_button: QPushButton | None = None
        self._available_qualities: tuple[str, ...] = ()
        self._active_quality: str | None = None
        self._position_slider: QSlider | None = None
        self._duration_label: QLabel | None = None
        self._position_label: QLabel | None = None
        self._play_button: IconButton | None = None
        self._bottom_play_button: IconButton | None = None
        self._volume_slider: QSlider | None = None
        self._volume_button: IconButton | None = None
        self._overlay: QWidget | None = None
        self._top_bar: QWidget | None = None
        self._bottom_bar: QWidget | None = None
        self._lock_bar: QWidget | None = None
        self._spinner: QWidget | None = None
        self._stage_label: QLabel | None = None
        self._web_view: QWidget | None = None
        self._video_widget: QWidget | None = None
        self._locked = False
        self._fullscreen = False
        self._muted = False
        self._dragging = False
        self._controls_visible = True
        self._skip_button: QPushButton | None = None
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(3000)
        self._hide_timer.timeout.connect(self._hide_controls)
        self._stage_timer = QTimer(self)
        self._stage_timer.setInterval(900)
        self._stage_timer.timeout.connect(self._next_stage)
        self._stages = (
            S.PLAYER_LOADING_EPISODE,
            S.PLAYER_LOADING_LINKS,
            S.PLAYER_LOADING_CONNECTING,
            S.PLAYER_LOADING_VIDEO,
        )
        self._stage_index = 0
        self._shortcuts: list[QShortcut] = []
        self._reload_on_show = False
        self._install_shortcuts()

    def create_loading_page(self) -> QWidget:
        theme = active_theme()
        host = QWidget(self)
        host.setStyleSheet(f"background-color: {theme.color('snackbar_background')};")
        layout = QVBoxLayout(host)
        layout.setContentsMargins(theme.space("xxl"), theme.space("xxl"), theme.space("xxl"), theme.space("xxl"))
        layout.addStretch(1)
        spinner = Spinner(56, parent=host)
        layout.addWidget(spinner, 0, Qt.AlignmentFlag.AlignHCenter)
        label = QLabel(S.PLAYER_LOADING_EPISODE, host)
        label.setStyleSheet(f"color: {theme.color('tooltip_text')};")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        layout.addStretch(1)
        return host

    def reload(self) -> None:
        self._stop_playback()
        super().reload()

    def populate(self) -> None:
        self._stop_playback()
        self._iframe_source = False
        self._locked = self._muted = self._dragging = False
        self._rate = 1.0
        self._controls_visible = True
        self.reset_content()
        page = QWidget(self)
        page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        stack = QStackedLayout(page)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        stack.setContentsMargins(0, 0, 0, 0)
        surface = VideoSurface(page)
        stack.addWidget(surface)
        overlay = QWidget(page)
        stack.addWidget(overlay)
        stack.setCurrentWidget(overlay)
        self._overlay = overlay
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setSpacing(0)
        self._top_bar = self._build_top_bar(overlay)
        overlay_layout.addWidget(self._top_bar)
        overlay_layout.addStretch(1)
        self._play_button = IconButton("pause", role="badge_text", size=56, tooltip=S.TOOLTIP_PLAY, parent=overlay)
        self._play_button.clicked.connect(self._toggle_play)
        overlay_layout.addWidget(self._play_button, 0, Qt.AlignmentFlag.AlignHCenter)
        overlay_layout.addStretch(1)
        self._skip_button = QPushButton(S.PLAYER_SKIP_OPENING, overlay)
        self._skip_button.setProperty("ui", "grey")
        self._skip_button.setIcon(icons.icon("seek_forward", "icon", 16))
        self._skip_button.clicked.connect(lambda: self._seek(90.0))
        overlay_layout.addWidget(self._skip_button, 0, Qt.AlignmentFlag.AlignHCenter)
        self._bottom_bar = self._build_bottom_bar(overlay)
        overlay_layout.addWidget(self._bottom_bar)
        self._lock_bar = self._build_lock_bar(overlay)
        overlay_layout.addWidget(self._lock_bar, 0, Qt.AlignmentFlag.AlignRight)
        self._lock_bar.hide()
        self._watch_pointer(overlay)
        self._replace_player_page(page)
        self.setFocus(Qt.FocusReason.OtherFocusReason)

        self._available_qualities = ()
        self._active_quality = None
        episode = self._resolve_stream()
        if episode is not None and episode.stream_url:
            self._iframe_source = bool(episode.iframe)
            stream_url = episode.stream_url
            if episode.iframe:
                # QtWebEngine has no H.264/AAC; resolve Kodik's direct HLS
                # manifest and let QMediaPlayer/FFmpeg decode it instead.
                resolved = resolve_iframe_stream(
                    episode.stream_url, quality=self.settings.quality
                )
                stream_url = resolved.url if resolved is not None else ""
                if resolved is not None and self._quality_button is not None:
                    self._available_qualities = tuple(f"{q}p" for q in resolved.available_qualities)
                    self._active_quality = f"{resolved.quality}p"
                    self._quality_button.setText(self._active_quality + (" ▾" if len(self._available_qualities) > 1 else ""))
                    self._quality_button.setEnabled(len(self._available_qualities) > 1)
                    if self.settings.quality != self._active_quality:
                        self._quality_button.setToolTip(
                            f"{self.settings.quality} недоступно у источника. Воспроизводится {self._active_quality}."
                        )
            if stream_url and self._start_media_player(page, stack, stream_url):
                surface.hide()
                self._show_controls()
                self.ctx.host.set_header(S.PLAYER_TITLE, self.release_title)
                return
            if episode.iframe and self._start_web_player(page, stack, episode.stream_url):
                surface.hide()
                overlay.hide()
                self.notify(S.PLAYER_STREAM_FALLBACK)
                self.ctx.host.set_header(S.PLAYER_TITLE, self.release_title)
                return

        if isinstance(self.repo, DemoRepository) or os.environ.get("ANX_UI_SMOKE_TEST") == "1":
            self._backend = StubPlayerBackend(parent=self)
            self._attach_backend(self._backend)
        else:
            message = "Видео недоступно для выбранной серии и источника"
            self._play_button.hide()
            self._skip_button.hide()
            label = QLabel(message, surface)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: white;")
            QVBoxLayout(surface).addWidget(label)
        self.ctx.host.set_header(S.PLAYER_TITLE, self.release_title)

    def _replace_player_page(self, page: QWidget) -> None:
        """Keep video and its overlay outside the screen's scroll area."""
        previous = self._player_page
        self._player_page = page
        self.stack.addWidget(page)
        if previous is not None:
            self.stack.removeWidget(previous)
            previous.deleteLater()

    def _stop_playback(self) -> None:
        backend, self._backend = self._backend, None
        if backend is not None:
            backend.blockSignals(True)
            backend.stop()
            backend.deleteLater()
        web, self._web_view = self._web_view, None
        if web is not None:
            web.stop()
            web.setUrl(QUrl("about:blank"))
        self._video_widget = None
        self._video_view = None
        self._hide_timer.stop()
        self._stage_timer.stop()

    def show_content(self) -> None:
        if self._player_page is not None:
            self.stack.setCurrentWidget(self._player_page)
            return
        super().show_content()

    def _resolve_stream(self):
        """Resolve the requested episode without silently playing another one."""
        if os.environ.get("ANX_UI_SMOKE_TEST") == "1":
            return None
        try:
            episodes = self.ctx.repo.fetch_episodes(
                self.release_id,
                type_id=self.payload.get("type_id"),
                source_id=self.payload.get("source_id"),
            )
        except Exception:
            return None
        if not episodes:
            return None
        wanted = int(self.payload.get("episode_id", 0) or 0)
        for episode in episodes:
            if episode.id == wanted:
                return episode
        if wanted:
            return None
        number = self.payload.get("episode_number")
        if number is None:
            return episodes[0]
        return next((episode for episode in episodes if episode.number == number), None)

    def _start_web_player(self, page: QWidget, stack, url: str) -> bool:
        try:
            from PySide6.QtWebEngineCore import QWebEngineSettings
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except Exception:
            return False
        web = QWebEngineView(page)
        try:
            web.settings().setAttribute(
                QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False
            )
        except Exception:
            pass
        # Kodik (and similar hosts) only render the player inside an iframe:
        # a top-level navigation is answered with "page does not exist".
        web.setHtml(_iframe_embed_html(url))
        stack.insertWidget(0, web)
        self._web_view = web
        return True

    def _start_media_player(self, page: QWidget, stack, url: str) -> bool:
        try:
            from PySide6.QtMultimediaWidgets import QGraphicsVideoItem  # noqa: F401
        except Exception:
            return False
        # QVideoWidget is a native window on Wayland and covers the controls
        # overlay. QGraphicsVideoItem is composited by Qt, so the overlay stays
        # visible and clickable above the picture.
        if self.settings.upscale_mode != "off":
            from ..upscale import UpscaleView

            view = UpscaleView(
                self.settings.upscale_mode, page,
                model=self.settings.upscale_model,
                passes=self.settings.upscale_passes,
                scale=self.settings.upscale_scale,
                sharp=self.settings.upscale_sharp,
            )
            if self._upscale_button is not None:
                self._upscale_button.setText("Anime4K: ожидание ▾")
            output = view.video_sink
            view.backend_changed.connect(self._on_upscale_backend)
        else:
            view = VideoView(page)
            output = view.video_item
        if self._upscale_button is not None:
            self._upscale_button.setEnabled(True)
        stack.insertWidget(0, view)
        self._video_widget = view
        self._video_view = view
        self._watch_pointer(view)
        self._backend = QtMediaBackend(url, output, parent=self)
        self._attach_backend(self._backend)
        self._backend.start()
        return True

    def _watch_pointer(self, widget: QWidget) -> None:
        widget.setMouseTracking(True)
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.setMouseTracking(True)
            child.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if event.type() in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress):
            self._show_controls()
        elif event.type() == QEvent.Type.MouseButtonDblClick:
            self._toggle_fullscreen()
        return super().eventFilter(obj, event)

    def _attach_backend(self, backend) -> None:
        backend.duration_changed.connect(self._on_duration)
        backend.position_changed.connect(self._on_position)
        backend.playing_changed.connect(self._on_playing)
        backend.buffering_changed.connect(self._on_buffering)
        backend.error_occurred.connect(self._on_error)
        if isinstance(backend, QtMediaBackend):
            backend.compressor = self.settings.audio_compressor
            backend.audio_effects.status_changed.connect(self._refresh_audio_tooltip)
        backend.set_volume(self._volume_slider.value())
        self._refresh_audio_tooltip()
        self._on_duration(backend.duration())
        self._on_position(backend.position())
        self._on_playing(backend.is_playing())

    def _build_top_bar(self, parent: QWidget) -> QWidget:
        theme = active_theme()
        bar = QFrame(parent)
        bar.setStyleSheet(
            f"background-color: {theme.alpha_color('player_scrim')};"
            "border: none;"
        )
        bar.setFixedHeight(theme.semantic("toolbar_height"))
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(theme.space("sm"), theme.space("sm"), theme.space("m"), theme.space("sm"))
        layout.setSpacing(theme.space("m"))
        back = IconButton("back", role="badge_text", size=24, tooltip=S.TOOLTIP_BACK, parent=bar)
        back.clicked.connect(self.ctx.host.go_back)
        layout.addWidget(back)
        text = QVBoxLayout()
        text.setSpacing(0)
        title = QLabel(self.release_title, bar)
        title.setStyleSheet(f"color: {theme.color('badge_text')}; font-weight: 500;")
        text.addWidget(title)
        episode = QLabel(self.episode_title, bar)
        episode.setStyleSheet(f"color: {theme.color('tooltip_text')}; font-size: {theme.px(13)}px;")
        text.addWidget(episode)
        layout.addLayout(text, 1)
        speed = QPushButton("1× ▾", bar)
        speed.setStyleSheet(f"color: {theme.color('badge_text')}; background: transparent;")
        speed.clicked.connect(lambda: self._speed_menu(speed))
        layout.addWidget(speed)
        quality = QPushButton("Качество: источник", bar)
        quality.setEnabled(False)
        quality.setStyleSheet(f"color: {theme.color('badge_text')}; background: transparent;")
        quality.clicked.connect(lambda: self._quality_menu(quality))
        layout.addWidget(quality)
        self._quality_button = quality
        upscale = QPushButton("Anime4K ▾", bar)
        upscale.setStyleSheet(quality.styleSheet())
        upscale.setEnabled(False)
        upscale.clicked.connect(lambda: self._upscale_menu(upscale))
        layout.addWidget(upscale)
        self._upscale_button = upscale
        lock = IconButton("lock", role="badge_text", size=22, tooltip=S.TOOLTIP_LOCK, parent=bar)
        lock.clicked.connect(self._toggle_lock)
        layout.addWidget(lock)
        return bar

    def _build_bottom_bar(self, parent: QWidget) -> QWidget:
        theme = active_theme()
        bar = QFrame(parent)
        bar.setStyleSheet(f"background-color: {theme.alpha_color('player_scrim')}; border: none;")
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(theme.space("m"), theme.space("sm"), theme.space("m"), theme.space("m"))
        layout.setSpacing(theme.space("xs"))
        slider_row = QHBoxLayout()
        slider_row.setSpacing(theme.space("m"))
        self._position_label = QLabel("00:00", bar)
        self._position_label.setStyleSheet(f"color: {theme.color('tooltip_text')}; font-size: {theme.px(12)}px;")
        slider_row.addWidget(self._position_label)
        self._position_slider = TimelineSlider(Qt.Orientation.Horizontal, bar)
        self._position_slider.setProperty("ui", "player")
        self._position_slider.setRange(0, 1000)
        self._position_slider.setValue(0)
        self._position_slider.sliderPressed.connect(self._on_slider_pressed)
        self._position_slider.sliderReleased.connect(self._on_slider_released)
        self._position_slider.seek_requested.connect(self._on_slider_released)
        slider_row.addWidget(self._position_slider, 1)
        self._duration_label = QLabel("00:00", bar)
        self._duration_label.setStyleSheet(f"color: {theme.color('tooltip_text')}; font-size: {theme.px(12)}px;")
        slider_row.addWidget(self._duration_label)
        layout.addLayout(slider_row)
        controls = QHBoxLayout()
        controls.setSpacing(theme.space("sm"))
        prev = IconButton("prev", role="badge_text", size=22, tooltip=S.TOOLTIP_PREV, parent=bar)
        prev.clicked.connect(lambda: self._change_episode(-1))
        controls.addWidget(prev)
        back10 = QPushButton(S.PLAYER_BACK_10, bar)
        back10.setStyleSheet(f"color: {theme.color('badge_text')}; background: transparent;")
        back10.clicked.connect(lambda: self._seek_relative(-self.settings.seek_seconds))
        controls.addWidget(back10)
        play = IconButton("play", role="badge_text", size=28, tooltip=S.TOOLTIP_PLAY, parent=bar)
        play.clicked.connect(self._toggle_play)
        controls.addWidget(play)
        self._bottom_play_button = play
        forward10 = QPushButton(S.PLAYER_FORWARD_10, bar)
        forward10.setStyleSheet(f"color: {theme.color('badge_text')}; background: transparent;")
        forward10.clicked.connect(lambda: self._seek_relative(self.settings.seek_seconds))
        controls.addWidget(forward10)
        next_button = IconButton("next", role="badge_text", size=22, tooltip=S.TOOLTIP_NEXT, parent=bar)
        next_button.clicked.connect(lambda: self._change_episode(1))
        controls.addWidget(next_button)
        controls.addStretch(1)
        self._volume_button = IconButton("volume", role="badge_text", size=20, tooltip=S.TOOLTIP_VOLUME, parent=bar)
        self._volume_button.clicked.connect(self._toggle_mute)
        controls.addWidget(self._volume_button)
        self._volume_slider = QSlider(Qt.Orientation.Horizontal, bar)
        self._volume_slider.setRange(0, 200)
        self._volume_slider.setValue(self.settings.player_volume)
        self._volume_slider.setFixedWidth(theme.px(90))
        self._volume_slider.valueChanged.connect(self._on_volume)
        controls.addWidget(self._volume_slider)
        audio = QPushButton("Звук ▾", bar)
        audio.clicked.connect(lambda: self._audio_menu(audio))
        controls.addWidget(audio)
        subs = QPushButton(S.PLAYER_SUBTITLES, bar)
        subs.setStyleSheet(f"color: {theme.color('badge_text')}; background: transparent;")
        subs.clicked.connect(lambda: self.notify(S.PLAYER_SUBTITLES))
        controls.addWidget(subs)
        voice = QPushButton(S.PLAYER_SOURCE, bar)
        voice.setStyleSheet(f"color: {theme.color('badge_text')}; background: transparent;")
        voice.clicked.connect(lambda: self._source_menu(voice))
        controls.addWidget(voice)
        pip = IconButton("pip", role="badge_text", size=20, tooltip=S.TOOLTIP_PIP, parent=bar)
        pip.clicked.connect(lambda: self.notify(S.PLAYER_PIP_STUB))
        controls.addWidget(pip)
        fullscreen = IconButton("fullscreen", role="badge_text", size=20, tooltip=S.TOOLTIP_FULLSCREEN, parent=bar)
        fullscreen.clicked.connect(self._toggle_fullscreen)
        controls.addWidget(fullscreen)
        layout.addLayout(controls)
        bar.setFixedHeight(max(theme.semantic("toolbar_height"), bar.sizeHint().height()))
        return bar

    def _build_lock_bar(self, parent: QWidget) -> QWidget:
        theme = active_theme()
        bar = QFrame(parent)
        bar.setStyleSheet(f"background-color: {theme.alpha_color('player_scrim')}; border: none;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(theme.space("m"), theme.space("sm"), theme.space("m"), theme.space("sm"))
        unlock = IconButton("unlock", role="badge_text", size=24, tooltip=S.PLAYER_UNLOCK, parent=bar)
        unlock.clicked.connect(self._toggle_lock)
        layout.addWidget(unlock)
        return bar

    # ------------------------------------------------------------------- state
    def _toggle_play(self) -> None:
        if self._backend:
            self._backend.toggle()

    def _on_playing(self, playing: bool) -> None:
        icon = "pause" if playing else "play"
        tooltip = S.PLAYER_PAUSE if playing else S.TOOLTIP_PLAY
        for button in (self._play_button, self._bottom_play_button):
            if button is not None:
                button.set_icon(icon)
                button.setToolTip(tooltip)
        self._hide_timer.start()

    def _on_buffering(self, buffering: bool) -> None:
        if self._play_button is not None:
            self._play_button.setEnabled(not buffering)
        if buffering:
            self._stage_timer.start()
        else:
            self._stage_timer.stop()
            if self._stage_label is not None:
                self._stage_label.hide()

    def _on_error(self, message: str) -> None:
        self._on_buffering(False)
        self._show_controls()
        self.notify(message)

    def _on_duration(self, duration: float) -> None:
        if self._duration_label is not None:
            self._duration_label.setText(format_timestamp(duration))

    def _on_position(self, position: float) -> None:
        if self._position_label is not None:
            self._position_label.setText(format_timestamp(position))
        if self._position_slider is not None and not self._dragging and self._backend:
            duration = self._backend.duration()
            self._position_slider.setValue(int(1000 * position / duration) if duration else 0)
        if self._skip_button is not None:
            self._skip_button.setVisible(
                self._controls_visible and 5 < position < 90
            )

    def _on_slider_pressed(self) -> None:
        self._dragging = True

    def _on_slider_released(self) -> None:
        self._dragging = False
        if self._backend and self._position_slider is not None:
            self._backend.seek(self._position_slider.value() / 1000 * self._backend.duration())

    def _seek(self, position: float) -> None:
        if self._backend:
            self._backend.seek(position)

    def _seek_relative(self, delta: float) -> None:
        if self._backend:
            self._backend.seek_relative(delta)
        self._show_controls()

    def _on_volume(self, value: int) -> None:
        if self._backend:
            self._backend.set_volume(value)
        if value:
            self.settings.player_volume = value
        self._muted = value == 0
        self._refresh_audio_tooltip()
        if self._volume_button is not None:
            self._volume_button.set_icon("volume_off" if self._muted else "volume")

    def _toggle_mute(self) -> None:
        self._muted = not self._muted
        if self._volume_slider is not None:
            self._volume_slider.setValue(0 if self._muted else self.settings.player_volume)
        if self._volume_button is not None:
            self._volume_button.set_icon("volume_off" if self._muted else "volume")

    def _refresh_audio_tooltip(self) -> None:
        if self._volume_slider is None:
            return
        volume = self._volume_slider.value()
        detail = f"Громкость: {volume}%"
        if isinstance(self._backend, QtMediaBackend):
            effects = self._backend.audio_effects
            if effects.unavailable_reason:
                detail += f" · {effects.unavailable_reason}"
            elif effects.active:
                detail += " · обработка PCM активна"
        self._volume_slider.setToolTip(detail)

    def _audio_menu(self, anchor: QPushButton) -> None:
        if not isinstance(self._backend, QtMediaBackend):
            return
        menu = QMenu(self)
        compressor = menu.addAction("Компрессия динамического диапазона")
        compressor.setCheckable(True)
        compressor.setChecked(self.settings.audio_compressor)
        if menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft())) is compressor:
            self.settings.audio_compressor = compressor.isChecked()
            if isinstance(self._backend, QtMediaBackend):
                self._backend.compressor = self.settings.audio_compressor
                self._backend.set_volume(self._volume_slider.value())
                self._refresh_audio_tooltip()

    def _speed_menu(self, anchor: QPushButton) -> None:
        menu = QMenu(self)
        actions = []
        for rate in (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
            action = menu.addAction(f"{rate:g}×")
            actions.append((rate, action))
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        for rate, action in actions:
            if chosen == action:
                if self._backend:
                    self._backend.set_rate(rate)
                anchor.setText(f"{rate:g}× ▾")
                break

    def _on_upscale_backend(self, backend: str) -> None:
        if self.sender() is not self._video_view or self._upscale_button is None:
            return
        if backend != "opengl":
            self._upscale_button.setText("Масштабирование Qt ▾")
            self._upscale_button.setToolTip("Обычное масштабирование, без CNN")
            return
        passes = self._video_view.effective_passes
        requested = self.settings.upscale_passes
        self._upscale_button.setText(f"Anime4K · {passes}/{requested} ▾")
        detail = f"Anime4K CNN {self.settings.upscale_model} · OpenGL · ×{self.settings.upscale_scale:g}"
        if self.settings.upscale_sharp:
            detail += " · усиление контуров"
        if passes != requested:
            detail += "; число прогонов снижено из-за лимита ресурсов"
        self._upscale_button.setToolTip(detail)

    def _upscale_menu(self, anchor: QPushButton) -> None:
        menu = QMenu(self)
        actions = {}

        def choices(parent, attribute, options):
            current = getattr(self.settings, attribute)
            for value, label in options:
                action = parent.addAction(label)
                action.setCheckable(True)
                action.setChecked(value == current)
                actions[action] = (attribute, value)

        maximum = menu.addAction("Максимум · UL ×4 + контуры")
        menu.addSeparator()
        choices(menu, "upscale_mode", (("off", "Выключено"), ("auto", "Авто"),
                                       ("opengl", "OpenGL · Anime4K"), ("cpu", "CPU · без CNN")))
        menu.addSeparator()
        choices(menu.addMenu("Модель CNN"), "upscale_model",
                (("S", "S · быстрее"), ("M", "M"), ("L", "L"),
                 ("VL", "VL"), ("UL", "UL · самая тяжёлая")))
        choices(menu.addMenu("Полных прогонов CNN"), "upscale_passes",
                ((1, "1 · нативный ×2"), (2, "2 · нативный ×4"), (3, "3 · нативный ×8")))
        choices(menu.addMenu("Масштаб обработки"), "upscale_scale",
                ((1.5, "×1,5"), (2, "×2"), (3, "×3"), (4, "×4")))
        choices(menu.addMenu("Усиление контуров"), "upscale_sharp",
                ((False, "Выключено"), (True, "Включено")))
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        if chosen is maximum:
            self.settings.upscale_mode = "auto"
            self.settings.upscale_model = "UL"
            self.settings.upscale_passes = 2
            self.settings.upscale_scale = 4
            self.settings.upscale_sharp = True
            self.reload()
            return
        selection = actions.get(chosen)
        if selection is not None:
            attribute, value = selection
            if getattr(self.settings, attribute) != value:
                setattr(self.settings, attribute, value)
                if attribute == "upscale_mode" or self.settings.upscale_mode in {"auto", "opengl"}:
                    self.reload()

    def _quality_menu(self, anchor: QPushButton) -> None:
        menu = QMenu(self)
        actions = []
        for quality in self._available_qualities:
            action = menu.addAction(quality)
            action.setCheckable(True)
            action.setChecked(quality == self._active_quality)
            actions.append((quality, action))
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        for quality, action in actions:
            if chosen == action and quality != self._active_quality:
                self.settings.quality = quality
                anchor.setText(f"{quality} ▾")
                self.notify(f"{S.PLAYER_QUALITY}: {quality}")
                if self._iframe_source:
                    self.ctx.host.reload_current()
                break

    def _source_menu(self, anchor: QWidget) -> None:
        menu = QMenu(self)
        type_id = self.payload.get("type_id")
        sources = self.repo.episode_sources(self.release_id, type_id)
        actions = [(source, menu.addAction(source.name)) for source in sources]
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        for source, action in actions:
            if chosen == action:
                payload = dict(self.payload)
                if source.id != payload.get("source_id") and payload.get("episode_number") is not None:
                    payload.pop("episode_id", None)
                payload["source_id"] = source.id
                if type_id is not None:
                    payload["type_id"] = type_id
                self.ctx.host.navigate("player", payload, push=False)
                break

    def _toggle_lock(self) -> None:
        self._locked = not self._locked
        if self._top_bar is not None:
            self._top_bar.setVisible(not self._locked)
        if self._bottom_bar is not None:
            self._bottom_bar.setVisible(not self._locked)
        if self._overlay is not None:
            self._overlay.setVisible(True)
        if self._lock_bar is not None:
            self._lock_bar.setVisible(self._locked)

    def _toggle_fullscreen(self) -> None:
        self._fullscreen = not self._fullscreen
        setter = getattr(self.ctx.host, "set_player_fullscreen", None)
        if callable(setter):
            setter(self._fullscreen)
        else:
            window = self.window()
            if self._fullscreen:
                window.showFullScreen()
            else:
                window.showNormal()
        self._show_controls()

    def _hide_controls(self) -> None:
        if self._locked:
            return
        self._controls_visible = False
        for widget in (self._top_bar, self._bottom_bar, self._skip_button, self._play_button):
            if widget is not None:
                widget.hide()

    def _show_controls(self) -> None:
        if self._backend is None:
            return
        if self._locked:
            if self._lock_bar is not None:
                self._lock_bar.show()
            return
        self._controls_visible = True
        if self._top_bar is not None:
            self._top_bar.show()
        if self._bottom_bar is not None:
            self._bottom_bar.show()
        if self._play_button is not None:
            self._play_button.show()
        if self._skip_button is not None and self._backend is not None:
            self._skip_button.setVisible(5 < self._backend.position() < 90)
        self._hide_timer.start()

    def _next_stage(self) -> None:
        self._stage_index = (self._stage_index + 1) % len(self._stages)
        if self._stage_label is not None:
            self._stage_label.setText(self._stages[self._stage_index])

    def _change_episode(self, delta: int) -> None:
        episodes = self.repo.fetch_episodes(
            self.release_id,
            type_id=self.payload.get("type_id"),
            source_id=self.payload.get("source_id"),
        )
        if not episodes:
            return
        episode_id = self.payload.get("episode_id")
        number = self.payload.get("episode_number")
        current = next((i for i, ep in enumerate(episodes) if ep.id == episode_id), None)
        if current is None:
            current = next((i for i, ep in enumerate(episodes) if ep.number == number), None)
        if current is None:
            return
        target = current + delta
        if target < 0 or target >= len(episodes):
            self.notify(S.RANDOM_EMPTY)
            return
        episode = episodes[target]
        payload = dict(self.payload)
        payload.update(
            {
                "release_id": self.release_id,
                "episode_id": episode.id,
                "episode_number": episode.number,
                "title": self.release_title,
                "episode": episode.title,
            }
        )
        self.open_route("player", payload, push=True)

    # --------------------------------------------------------------- shortcuts
    def _install_shortcuts(self) -> None:
        def bind(sequence: str, handler) -> None:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(handler)
            self._shortcuts.append(shortcut)

        bind("Space", self._toggle_play)
        bind("Left", lambda: self._seek_relative(-self.settings.seek_seconds))
        bind("Right", lambda: self._seek_relative(self.settings.seek_seconds))
        bind("Up", lambda: self._nudge_volume(5))
        bind("Down", lambda: self._nudge_volume(-5))
        bind("F", self._toggle_fullscreen)
        bind("M", self._toggle_mute)
        bind("L", self._toggle_lock)
        bind("[", lambda: self._nudge_rate(-0.25))
        bind("]", lambda: self._nudge_rate(0.25))

    def _nudge_volume(self, delta: int) -> None:
        if self._volume_slider is not None:
            self._volume_slider.setValue(self._volume_slider.value() + delta)

    def _nudge_rate(self, delta: float) -> None:
        if self._backend is None:
            return
        current = getattr(self, "_rate", 1.0) + delta
        current = max(0.25, min(2.0, current))
        self._rate = current
        self._backend.set_rate(current)
        self.notify(f"{S.PLAYER_SPEED}: {current:g}×")

    def handle_escape(self) -> bool:
        if self._fullscreen:
            self._toggle_fullscreen()
            return True
        if self._locked:
            self._toggle_lock()
            return True
        return False

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        self._show_controls()
        super().mouseMoveEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if self._reload_on_show:
            self._reload_on_show = False
            self.reload()

    def hideEvent(self, event) -> None:  # noqa: N802
        if not event.spontaneous():
            if self._activated:
                self._load_timer.stop()
                self._reload_on_show = True
            self._stop_playback()
        super().hideEvent(event)
