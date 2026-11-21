"""Asynchronous remote image cache for posters and artwork.

The UI never blocks on image downloads: widgets ask the cache for a URL and
repaint when the pixmap arrives.  The cache is process-wide and bounded.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Callable

from PySide6.QtCore import QRectF, Qt, QUrl
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

ImageCallback = Callable[[QPixmap | None], None]


class ImageCache:
    def __init__(self, limit: int = 256) -> None:
        self._limit = limit
        self._cache: OrderedDict[str, QPixmap] = OrderedDict()
        self._pending: dict[str, list[ImageCallback]] = {}
        self._manager: QNetworkAccessManager | None = None

    def _network(self) -> QNetworkAccessManager:
        if self._manager is None:
            manager = QNetworkAccessManager()
            manager.setRedirectPolicy(
                QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy
            )
            self._manager = manager
        return self._manager

    def cached(self, url: str) -> QPixmap | None:
        if not url:
            return None
        pixmap = self._cache.get(url)
        if pixmap is not None:
            self._cache.move_to_end(url)
        return pixmap

    def load(self, url: str, callback: ImageCallback) -> None:
        if not url:
            callback(None)
            return
        pixmap = self.cached(url)
        if pixmap is not None:
            callback(pixmap)
            return
        if url in self._pending:
            self._pending[url].append(callback)
            return
        self._pending[url] = [callback]
        request = QNetworkRequest(QUrl(url))
        request.setHeader(
            QNetworkRequest.KnownHeaders.UserAgentHeader, "anx-desktop/0.1"
        )
        reply = self._network().get(request)
        reply.finished.connect(lambda: self._finish(url, reply))

    def _finish(self, url: str, reply: QNetworkReply) -> None:
        pixmap: QPixmap | None = None
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            candidate = QPixmap()
            if candidate.loadFromData(data):
                pixmap = candidate
        reply.deleteLater()
        callbacks = self._pending.pop(url, [])
        if pixmap is not None and not pixmap.isNull():
            self._cache[url] = pixmap
            self._cache.move_to_end(url)
            while len(self._cache) > self._limit:
                self._cache.popitem(last=False)
        for callback in callbacks:
            try:
                callback(pixmap)
            except RuntimeError:
                # A widget was destroyed while its image was in flight.
                continue


images = ImageCache()


def paint_image(
    painter: QPainter,
    rect: QRectF,
    pixmap: QPixmap,
    radius: float,
) -> None:
    """Draw ``pixmap`` cropped to fill ``rect`` with rounded corners."""

    if pixmap.isNull() or rect.isEmpty():
        return
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    target = rect.toRect()
    scaled = pixmap.scaled(
        target.size(),
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = target.x() + (target.width() - scaled.width()) // 2
    y = target.y() + (target.height() - scaled.height()) // 2
    painter.save()
    painter.setClipPath(path)
    painter.drawPixmap(x, y, scaled)
    painter.restore()
