"""Neutral, icon-font-free icon set drawn with QPainter.

The clean room does not copy Anixart assets.  Every glyph here is an original
24x24 line/fill drawing mapped from the semantic list in the style guide.
Colours come from theme tokens.
"""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)

from .theme import ThemeManager
from .tokens import tokens as canonical_tokens


def _theme() -> ThemeManager:
    manager = ThemeManager._active  # type: ignore[attr-defined]
    if manager is None:  # pragma: no cover - defensive
        manager = ThemeManager(None, canonical_tokens())
    return manager


def _pen(color: QColor, width: float = 2.0) -> QPen:
    pen = QPen(color)
    pen.setWidthF(width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _star_path() -> QPainterPath:
    path = QPainterPath()
    points = []
    for index in range(10):
        angle = -90 + index * 36
        import math

        radius = 9.0 if index % 2 == 0 else 3.8
        radians = math.radians(angle)
        points.append(QPointF(12 + radius * math.cos(radians), 12 + radius * math.sin(radians)))
    path.moveTo(points[0])
    for point in points[1:]:
        path.lineTo(point)
    path.closeSubpath()
    return path


def _heart_path() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(12, 20)
    path.cubicTo(4, 14.5, 2.4, 10.6, 4.2, 6.9)
    path.cubicTo(6.2, 3.0, 11.2, 3.8, 12, 7.2)
    path.cubicTo(12.8, 3.8, 17.8, 3.0, 19.8, 6.9)
    path.cubicTo(21.6, 10.6, 20.0, 14.5, 12, 20)
    path.closeSubpath()
    return path


def _draw(name: str, painter: QPainter, color: QColor) -> None:
    painter.setPen(_pen(color))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    filled = color
    if name in {"play"}:
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygonF([QPointF(8, 5), QPointF(19, 12), QPointF(8, 19)]))
        return
    if name == "pause":
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(7, 5, 3.5, 14), 1, 1)
        painter.drawRoundedRect(QRectF(13.5, 5, 3.5, 14), 1, 1)
        return
    if name in {"star", "star_outline"}:
        painter.setBrush(filled if name == "star" else Qt.BrushStyle.NoBrush)
        painter.drawPath(_star_path())
        return
    if name in {"heart", "heart_outline"}:
        painter.setBrush(filled if name == "heart" else Qt.BrushStyle.NoBrush)
        painter.drawPath(_heart_path())
        return
    if name == "home":
        path = QPainterPath()
        path.moveTo(3.5, 10.5)
        path.lineTo(12, 3.5)
        path.lineTo(20.5, 10.5)
        path.lineTo(20.5, 20.5)
        path.lineTo(14.5, 20.5)
        path.lineTo(14.5, 14)
        path.lineTo(9.5, 14)
        path.lineTo(9.5, 20.5)
        path.lineTo(3.5, 20.5)
        path.closeSubpath()
        painter.drawPath(path)
        return
    if name == "discover":
        painter.drawEllipse(QRectF(3, 3, 18, 18))
        path = QPainterPath()
        path.moveTo(15.5, 8.5)
        path.lineTo(13.2, 13.2)
        path.lineTo(8.5, 15.5)
        path.lineTo(10.8, 10.8)
        path.closeSubpath()
        painter.drawPath(path)
        return
    if name == "bookmarks":
        path = QPainterPath()
        path.moveTo(6, 3.5)
        path.lineTo(18, 3.5)
        path.lineTo(18, 20.5)
        path.lineTo(12, 15.8)
        path.lineTo(6, 20.5)
        path.closeSubpath()
        painter.drawPath(path)
        return
    if name == "feed":
        painter.drawRoundedRect(QRectF(3.5, 4, 17, 16), 2.5, 2.5)
        painter.drawLine(QPointF(7, 9), QPointF(17, 9))
        painter.drawLine(QPointF(7, 12.5), QPointF(17, 12.5))
        painter.drawLine(QPointF(7, 16), QPointF(13, 16))
        return
    if name == "search":
        painter.drawEllipse(QRectF(4, 4, 12, 12))
        painter.drawLine(QPointF(14.2, 14.2), QPointF(20, 20))
        return
    if name == "sun":
        painter.drawEllipse(QRectF(8, 8, 8, 8))
        for index in range(8):
            import math

            angle = math.radians(index * 45)
            inner = QPointF(12 + 6.4 * math.cos(angle), 12 + 6.4 * math.sin(angle))
            outer = QPointF(12 + 9.2 * math.cos(angle), 12 + 9.2 * math.sin(angle))
            painter.drawLine(inner, outer)
        return
    if name == "moon":
        outer = QPainterPath()
        outer.addEllipse(QRectF(4.5, 2.5, 16, 19))
        inner = QPainterPath()
        inner.addEllipse(QRectF(11.5, 4.5, 15, 17))
        crescent = outer.subtracted(inner)
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(crescent)
        return
    if name == "settings":
        painter.save()
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(8):
            painter.save()
            painter.translate(12, 12)
            painter.rotate(index * 45)
            painter.drawRoundedRect(QRectF(-1.8, -10.5, 3.6, 5.0), 1.0, 1.0)
            painter.restore()
        painter.drawEllipse(QRectF(6.5, 6.5, 11, 11))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.drawEllipse(QRectF(9.8, 9.8, 4.4, 4.4))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.restore()
        return
    if name == "bell":
        path = QPainterPath()
        path.moveTo(5.5, 16.5)
        path.lineTo(5.5, 11)
        path.cubicTo(5.5, 6.8, 8.2, 4.5, 12, 4.5)
        path.cubicTo(15.8, 4.5, 18.5, 6.8, 18.5, 11)
        path.lineTo(18.5, 16.5)
        path.lineTo(20, 18)
        path.lineTo(4, 18)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawArc(QRectF(9.5, 18, 5, 3.5), 180 * 16, 180 * 16)
        return
    if name == "user":
        painter.drawEllipse(QRectF(8, 4, 8, 8))
        path = QPainterPath()
        path.moveTo(4.5, 20.5)
        path.cubicTo(5.2, 15.2, 8.2, 13.5, 12, 13.5)
        path.cubicTo(15.8, 13.5, 18.8, 15.2, 19.5, 20.5)
        painter.drawPath(path)
        return
    if name == "back":
        painter.drawLine(QPointF(19, 12), QPointF(5, 12))
        painter.drawLine(QPointF(5, 12), QPointF(11, 6))
        painter.drawLine(QPointF(5, 12), QPointF(11, 18))
        return
    if name == "forward":
        painter.drawLine(QPointF(5, 12), QPointF(19, 12))
        painter.drawLine(QPointF(19, 12), QPointF(13, 6))
        painter.drawLine(QPointF(19, 12), QPointF(13, 18))
        return
    if name == "chevron_down":
        painter.drawLine(QPointF(7, 9.5), QPointF(12, 14.5))
        painter.drawLine(QPointF(12, 14.5), QPointF(17, 9.5))
        return
    if name == "chevron_up":
        painter.drawLine(QPointF(7, 14.5), QPointF(12, 9.5))
        painter.drawLine(QPointF(12, 9.5), QPointF(17, 14.5))
        return
    if name == "chevron_left":
        painter.drawLine(QPointF(14.5, 7), QPointF(9.5, 12))
        painter.drawLine(QPointF(9.5, 12), QPointF(14.5, 17))
        return
    if name == "chevron_right":
        painter.drawLine(QPointF(9.5, 7), QPointF(14.5, 12))
        painter.drawLine(QPointF(14.5, 12), QPointF(9.5, 17))
        return
    if name == "close":
        painter.drawLine(QPointF(6, 6), QPointF(18, 18))
        painter.drawLine(QPointF(18, 6), QPointF(6, 18))
        return
    if name == "refresh":
        painter.drawArc(QRectF(4, 4, 16, 16), 40 * 16, 280 * 16)
        painter.drawLine(QPointF(18.5, 4.5), QPointF(18.8, 9.4))
        painter.drawLine(QPointF(18.8, 9.4), QPointF(14.1, 8.2))
        return
    if name == "filter":
        for x1, x2, y in ((4, 20, 7), (7, 17, 12), (9, 15, 17)):
            painter.drawLine(QPointF(x1, y), QPointF(x2, y))
        painter.setBrush(filled)
        painter.drawEllipse(QRectF(14.5, 5, 4, 4))
        painter.drawEllipse(QRectF(7.0, 10, 4, 4))
        painter.drawEllipse(QRectF(12.0, 15, 4, 4))
        return
    if name == "sort":
        painter.drawLine(QPointF(8, 4), QPointF(8, 20))
        painter.drawLine(QPointF(8, 4), QPointF(4.5, 8))
        painter.drawLine(QPointF(8, 4), QPointF(11.5, 8))
        painter.drawLine(QPointF(16, 20), QPointF(16, 4))
        painter.drawLine(QPointF(16, 20), QPointF(12.5, 16))
        painter.drawLine(QPointF(16, 20), QPointF(19.5, 16))
        return
    if name == "shuffle":
        path = QPainterPath()
        path.moveTo(4, 7)
        path.lineTo(8, 7)
        path.cubicTo(12, 7, 12, 17, 16, 17)
        path.lineTo(20, 17)
        painter.drawPath(path)
        path = QPainterPath()
        path.moveTo(4, 17)
        path.lineTo(8, 17)
        path.cubicTo(11, 17, 13, 7, 16, 7)
        path.lineTo(20, 7)
        painter.drawPath(path)
        painter.drawLine(QPointF(17, 4), QPointF(20, 7))
        painter.drawLine(QPointF(17, 10), QPointF(20, 7))
        painter.drawLine(QPointF(17, 14), QPointF(20, 17))
        painter.drawLine(QPointF(17, 20), QPointF(20, 17))
        return
    if name == "plus":
        painter.drawLine(QPointF(12, 5), QPointF(12, 19))
        painter.drawLine(QPointF(5, 12), QPointF(19, 12))
        return
    if name == "minus":
        painter.drawLine(QPointF(5, 12), QPointF(19, 12))
        return
    if name == "check":
        painter.drawLine(QPointF(5, 12.5), QPointF(10, 17.5))
        painter.drawLine(QPointF(10, 17.5), QPointF(19.5, 6.5))
        return
    if name == "check_circle":
        painter.drawEllipse(QRectF(3, 3, 18, 18))
        painter.drawLine(QPointF(7.5, 12.2), QPointF(10.8, 15.5))
        painter.drawLine(QPointF(10.8, 15.5), QPointF(16.8, 8.5))
        return
    if name == "circle":
        painter.drawEllipse(QRectF(4, 4, 16, 16))
        return
    if name == "calendar":
        painter.drawRoundedRect(QRectF(3.5, 5, 17, 15.5), 2, 2)
        painter.drawLine(QPointF(3.5, 9.5), QPointF(20.5, 9.5))
        painter.drawLine(QPointF(7.5, 3), QPointF(7.5, 6.5))
        painter.drawLine(QPointF(16.5, 3), QPointF(16.5, 6.5))
        return
    if name == "history":
        painter.drawEllipse(QRectF(4, 4, 16, 16))
        painter.drawLine(QPointF(12, 7.5), QPointF(12, 12))
        painter.drawLine(QPointF(12, 12), QPointF(16, 14))
        return
    if name == "list":
        for y in (6, 12, 18):
            painter.setBrush(filled)
            painter.drawEllipse(QRectF(4, y - 1.3, 2.6, 2.6))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(QPointF(9, y), QPointF(20, y))
        return
    if name == "download":
        painter.drawLine(QPointF(12, 4), QPointF(12, 15))
        painter.drawLine(QPointF(12, 15), QPointF(7.5, 10.5))
        painter.drawLine(QPointF(12, 15), QPointF(16.5, 10.5))
        painter.drawLine(QPointF(4.5, 19), QPointF(19.5, 19))
        return
    if name == "trash":
        painter.drawLine(QPointF(4.5, 6.5), QPointF(19.5, 6.5))
        painter.drawLine(QPointF(9, 3.5), QPointF(15, 3.5))
        painter.drawRoundedRect(QRectF(6, 6.5, 12, 14), 1.5, 1.5)
        painter.drawLine(QPointF(10, 10), QPointF(10, 17))
        painter.drawLine(QPointF(14, 10), QPointF(14, 17))
        return
    if name == "pencil":
        path = QPainterPath()
        path.moveTo(4, 20)
        path.lineTo(5.2, 15.3)
        path.lineTo(16.4, 4.1)
        path.lineTo(19.9, 7.6)
        path.lineTo(8.7, 18.8)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(14.5, 6), QPointF(18, 9.5))
        return
    if name == "crown":
        path = QPainterPath()
        path.moveTo(4, 17)
        path.lineTo(4, 8)
        path.lineTo(8, 11)
        path.lineTo(12, 5.5)
        path.lineTo(16, 11)
        path.lineTo(20, 8)
        path.lineTo(20, 17)
        path.closeSubpath()
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
        return
    if name in {"verified", "badge"}:
        painter.drawEllipse(QRectF(3.5, 3.5, 17, 17))
        painter.drawLine(QPointF(8, 12.2), QPointF(11, 15.2))
        painter.drawLine(QPointF(11, 15.2), QPointF(16.3, 8.7))
        return
    if name == "online":
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(6, 6, 12, 12))
        return
    if name == "dot":
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(8.5, 8.5, 7, 7))
        return
    if name == "next":
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygonF([QPointF(7, 5), QPointF(16, 12), QPointF(7, 19)]))
        painter.drawRoundedRect(QRectF(16.5, 5, 2.6, 14), 1, 1)
        return
    if name == "prev":
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygonF([QPointF(17, 5), QPointF(8, 12), QPointF(17, 19)]))
        painter.drawRoundedRect(QRectF(4.9, 5, 2.6, 14), 1, 1)
        return
    if name == "seek_back":
        painter.drawArc(QRectF(4, 5, 16, 16), 90 * 16, 240 * 16)
        painter.drawLine(QPointF(4.5, 5.5), QPointF(4.8, 10.4))
        painter.drawLine(QPointF(4.8, 10.4), QPointF(9.6, 9.3))
        return
    if name == "seek_forward":
        painter.drawArc(QRectF(4, 5, 16, 16), -150 * 16, 240 * 16)
        painter.drawLine(QPointF(19.5, 5.5), QPointF(19.2, 10.4))
        painter.drawLine(QPointF(19.2, 10.4), QPointF(14.4, 9.3))
        return
    if name in {"volume", "volume_off"}:
        path = QPainterPath()
        path.moveTo(4, 9.5)
        path.lineTo(7.5, 9.5)
        path.lineTo(12, 5)
        path.lineTo(12, 19)
        path.lineTo(7.5, 14.5)
        path.lineTo(4, 14.5)
        path.closeSubpath()
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
        painter.setPen(_pen(color))
        if name == "volume":
            painter.drawArc(QRectF(11.5, 8, 8, 8), -60 * 16, 120 * 16)
            painter.drawArc(QRectF(12.5, 5.5, 9.5, 13), -55 * 16, 110 * 16)
        else:
            painter.drawLine(QPointF(15, 9), QPointF(20, 15))
            painter.drawLine(QPointF(20, 9), QPointF(15, 15))
        return
    if name in {"fullscreen", "exit_fullscreen"}:
        if name == "fullscreen":
            for x, y, dx, dy in ((4, 4, 1, 1), (20, 4, -1, 1), (4, 20, 1, -1), (20, 20, -1, -1)):
                painter.drawLine(QPointF(x, y), QPointF(x + 5 * dx, y))
                painter.drawLine(QPointF(x, y), QPointF(x, y + 5 * dy))
        else:
            for x, y, dx, dy in ((9, 9, -1, -1), (15, 9, 1, -1), (9, 15, -1, 1), (15, 15, 1, 1)):
                painter.drawLine(QPointF(x, y), QPointF(x + 5 * dx, y))
                painter.drawLine(QPointF(x, y), QPointF(x, y + 5 * dy))
        return
    if name == "pip":
        painter.drawRoundedRect(QRectF(3, 4.5, 18, 15), 2, 2)
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(11.5, 11, 8, 7), 1, 1)
        return
    if name in {"lock", "unlock"}:
        painter.drawRoundedRect(QRectF(5, 10.5, 14, 10), 2, 2)
        painter.drawArc(QRectF(8, 4, 8, 11), 0, 180 * 16)
        if name == "unlock":
            painter.drawLine(QPointF(16, 8.5), QPointF(16, 5.5))
            painter.drawArc(QRectF(11.5, 4, 6, 6), 0, 160 * 16)
        return
    if name == "subtitles":
        painter.drawRoundedRect(QRectF(3.5, 5, 17, 14), 2, 2)
        painter.drawLine(QPointF(7, 11), QPointF(13, 11))
        painter.drawLine(QPointF(7, 15), QPointF(17, 15))
        return
    if name == "speed":
        painter.drawArc(QRectF(4, 5, 16, 16), 0, 180 * 16)
        painter.drawLine(QPointF(12, 13), QPointF(16.5, 8))
        return
    if name == "quality":
        painter.drawRoundedRect(QRectF(3, 6, 18, 12), 2, 2)
        painter.drawLine(QPointF(8, 10), QPointF(8, 14))
        painter.drawLine(QPointF(8, 10), QPointF(12, 10))
        painter.drawLine(QPointF(8, 12), QPointF(11, 12))
        painter.drawLine(QPointF(15.5, 10), QPointF(15.5, 14))
        painter.drawLine(QPointF(15.5, 10), QPointF(18.5, 10))
        painter.drawLine(QPointF(15.5, 12), QPointF(18, 12))
        return
    if name == "article":
        painter.drawRoundedRect(QRectF(4.5, 3.5, 15, 17), 2, 2)
        painter.drawLine(QPointF(8, 8), QPointF(16, 8))
        painter.drawLine(QPointF(8, 12), QPointF(16, 12))
        painter.drawLine(QPointF(8, 16), QPointF(13, 16))
        return
    if name == "channel":
        painter.drawEllipse(QRectF(9, 9, 6, 6))
        painter.drawArc(QRectF(5, 5, 14, 14), 45 * 16, 90 * 16)
        painter.drawArc(QRectF(5, 5, 14, 14), 225 * 16, 90 * 16)
        painter.drawArc(QRectF(2, 2, 20, 20), 45 * 16, 90 * 16)
        painter.drawArc(QRectF(2, 2, 20, 20), 225 * 16, 90 * 16)
        return
    if name == "health":
        path = QPainterPath()
        path.moveTo(12, 3)
        path.lineTo(20, 6)
        path.lineTo(20, 12)
        path.cubicTo(20, 17, 16.5, 20, 12, 21.5)
        path.cubicTo(7.5, 20, 4, 17, 4, 12)
        path.lineTo(4, 6)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(8, 12), QPointF(11, 15))
        painter.drawLine(QPointF(11, 15), QPointF(16, 9))
        return
    if name == "collection":
        painter.drawRoundedRect(QRectF(3.5, 4, 17, 4.5), 1.5, 1.5)
        painter.drawRoundedRect(QRectF(4.5, 10, 15, 4.5), 1.5, 1.5)
        painter.drawRoundedRect(QRectF(5.5, 16, 13, 4.5), 1.5, 1.5)
        return
    if name == "qr":
        for rect in (QRectF(3.5, 3.5, 6, 6), QRectF(14.5, 3.5, 6, 6), QRectF(3.5, 14.5, 6, 6)):
            painter.drawRoundedRect(rect, 1, 1)
            painter.drawRect(rect.adjusted(1.6, 1.6, -1.6, -1.6))
        painter.drawRect(QRectF(14, 14, 3, 3))
        painter.drawRect(QRectF(18.5, 14, 2, 2))
        painter.drawRect(QRectF(14, 18.5, 2, 2))
        painter.drawRect(QRectF(18, 18, 3, 3))
        return
    if name == "mail":
        painter.drawRoundedRect(QRectF(3, 5, 18, 14), 2, 2)
        painter.drawLine(QPointF(4, 7), QPointF(12, 13))
        painter.drawLine(QPointF(20, 7), QPointF(12, 13))
        return
    if name == "key":
        painter.drawEllipse(QRectF(4, 7, 9, 9))
        painter.drawLine(QPointF(12.5, 13), QPointF(20, 20.5))
        painter.drawLine(QPointF(16.5, 17), QPointF(18.5, 15))
        painter.drawLine(QPointF(18.5, 19), QPointF(20.5, 17))
        return
    if name in {"eye", "eye_off"}:
        path = QPainterPath()
        path.moveTo(3, 12)
        path.cubicTo(6, 6.5, 18, 6.5, 21, 12)
        path.cubicTo(18, 17.5, 6, 17.5, 3, 12)
        painter.drawPath(path)
        painter.drawEllipse(QRectF(9, 9, 6, 6))
        if name == "eye_off":
            painter.drawLine(QPointF(5, 5), QPointF(19, 19))
        return
    if name == "microphone":
        painter.drawRoundedRect(QRectF(9, 3, 6, 11), 3, 3)
        painter.drawArc(QRectF(6, 8, 12, 10), 180 * 16, 180 * 16)
        painter.drawLine(QPointF(12, 18), QPointF(12, 21))
        painter.drawLine(QPointF(9, 21), QPointF(15, 21))
        return
    if name == "external":
        painter.drawRoundedRect(QRectF(4, 4, 16, 16), 2, 2)
        painter.drawLine(QPointF(11, 13), QPointF(19, 5))
        painter.drawLine(QPointF(13, 5), QPointF(19, 5))
        painter.drawLine(QPointF(19, 5), QPointF(19, 11))
        return
    if name == "link":
        painter.drawArc(QRectF(3, 9, 9, 7), 60 * 16, 220 * 16)
        painter.drawArc(QRectF(12, 8, 9, 7), 240 * 16, 220 * 16)
        painter.drawLine(QPointF(9, 12), QPointF(15, 12))
        return
    if name == "report":
        painter.drawLine(QPointF(6, 3), QPointF(6, 21))
        path = QPainterPath()
        path.moveTo(6, 4)
        path.lineTo(19, 4)
        path.lineTo(16, 9)
        path.lineTo(19, 14)
        path.lineTo(6, 14)
        painter.drawPath(path)
        return
    if name == "share":
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(14.5, 3, 5, 5))
        painter.drawEllipse(QRectF(3.5, 9.5, 5, 5))
        painter.drawEllipse(QRectF(14.5, 16, 5, 5))
        painter.setPen(_pen(color, 1.8))
        painter.drawLine(QPointF(8.3, 11.5), QPointF(15, 6.5))
        painter.drawLine(QPointF(8.3, 12.5), QPointF(15, 17.5))
        return
    if name == "globe":
        painter.drawEllipse(QRectF(3, 3, 18, 18))
        painter.drawLine(QPointF(3.5, 12), QPointF(20.5, 12))
        painter.drawEllipse(QRectF(8, 3.5, 8, 17))
        return
    if name == "comment":
        path = QPainterPath()
        path.addRoundedRect(QRectF(3.5, 4, 17, 13), 3, 3)
        painter.drawPath(path)
        painter.drawLine(QPointF(8, 17), QPointF(7, 21))
        painter.drawLine(QPointF(7, 21), QPointF(12, 17))
        return
    if name == "repost":
        painter.drawArc(QRectF(4, 5, 16, 14), 30 * 16, 250 * 16)
        painter.drawLine(QPointF(17.5, 4.5), QPointF(20.3, 7.8))
        painter.drawLine(QPointF(20.3, 7.8), QPointF(16.5, 9.1))
        return
    if name in {"like", "dislike"}:
        path = QPainterPath()
        path.moveTo(3.5, 10)
        path.lineTo(7, 10)
        path.lineTo(7, 20)
        path.lineTo(3.5, 20)
        path.closeSubpath()
        painter.drawPath(path)
        path = QPainterPath()
        if name == "like":
            path.moveTo(8, 12)
            path.lineTo(12, 4.5)
            path.cubicTo(14.5, 4.5, 14.5, 7, 14, 9.5)
            path.lineTo(19.5, 9.5)
            path.cubicTo(21, 9.5, 21, 11, 20.4, 12.5)
            path.lineTo(18.4, 18.5)
            path.cubicTo(18, 19.6, 17, 20, 16, 20)
            path.lineTo(8, 20)
            path.closeSubpath()
        else:
            path.moveTo(8, 12)
            path.lineTo(12, 19.5)
            path.cubicTo(14.5, 19.5, 14.5, 17, 14, 14.5)
            path.lineTo(19.5, 14.5)
            path.cubicTo(21, 14.5, 21, 13, 20.4, 11.5)
            path.lineTo(18.4, 5.5)
            path.cubicTo(18, 4.4, 17, 4, 16, 4)
            path.lineTo(8, 4)
            path.closeSubpath()
        painter.drawPath(path)
        return
    if name == "more":
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        for x in (6, 12, 18):
            painter.drawEllipse(QRectF(x - 1.4, 10.6, 2.8, 2.8))
        return
    if name in {"warning", "info", "error"}:
        if name == "warning":
            path = QPainterPath()
            path.moveTo(12, 3.5)
            path.lineTo(21, 20)
            path.lineTo(3, 20)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawLine(QPointF(12, 9), QPointF(12, 14))
            painter.setBrush(filled)
            painter.drawEllipse(QRectF(10.9, 16, 2.2, 2.2))
        else:
            painter.drawEllipse(QRectF(3.5, 3.5, 17, 17))
            if name == "info":
                painter.drawLine(QPointF(12, 11), QPointF(12, 17))
            else:
                painter.drawLine(QPointF(12, 7.5), QPointF(12, 13))
            painter.setBrush(filled)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(10.9, 6.7 if name == "error" else 16.7, 2.2, 2.2))
        return
    if name in {"folder", "image", "cloud", "ad", "memory", "bug", "rules", "update", "logout", "auth"}:
        # Neutral fallbacks with simple, readable geometry.
        if name == "folder":
            path = QPainterPath()
            path.moveTo(3, 6)
            path.lineTo(10, 6)
            path.lineTo(12, 8)
            path.lineTo(21, 8)
            path.lineTo(21, 19)
            path.lineTo(3, 19)
            path.closeSubpath()
            painter.drawPath(path)
        elif name == "image":
            painter.drawRoundedRect(QRectF(3, 4.5, 18, 15), 2, 2)
            painter.drawEllipse(QRectF(7, 8, 3, 3))
            painter.drawLine(QPointF(4, 17), QPointF(9.5, 12))
            painter.drawLine(QPointF(9.5, 12), QPointF(13.5, 16))
            painter.drawLine(QPointF(13.5, 16), QPointF(17.5, 12))
            painter.drawLine(QPointF(17.5, 12), QPointF(20.5, 15))
        elif name == "cloud":
            painter.drawArc(QRectF(5, 8, 9, 9), 0, 180 * 16)
            painter.drawArc(QRectF(10, 6, 9, 10), 0, 180 * 16)
            painter.drawLine(QPointF(7, 17), QPointF(18, 17))
        elif name == "ad":
            painter.drawRoundedRect(QRectF(3.5, 5.5, 17, 13), 2, 2)
            painter.drawLine(QPointF(7, 14), QPointF(9, 9))
            painter.drawLine(QPointF(9, 9), QPointF(11, 14))
            painter.drawLine(QPointF(7.6, 12), QPointF(10.4, 12))
            painter.drawLine(QPointF(14, 9), QPointF(14, 14))
            painter.drawEllipse(QRectF(12.7, 11.7, 2.6, 2.6))
        elif name == "memory":
            painter.drawRoundedRect(QRectF(5, 5, 14, 14), 2, 2)
            painter.drawRoundedRect(QRectF(9, 9, 6, 6), 1, 1)
            for value in (8, 12, 16):
                painter.drawLine(QPointF(value, 2.5), QPointF(value, 5))
                painter.drawLine(QPointF(value, 19), QPointF(value, 21.5))
                painter.drawLine(QPointF(2.5, value), QPointF(5, value))
                painter.drawLine(QPointF(19, value), QPointF(21.5, value))
        elif name == "bug":
            painter.drawRoundedRect(QRectF(7, 7, 10, 12), 4, 4)
            painter.drawLine(QPointF(4, 10), QPointF(7, 11))
            painter.drawLine(QPointF(20, 10), QPointF(17, 11))
            painter.drawLine(QPointF(4, 15), QPointF(7, 15))
            painter.drawLine(QPointF(20, 15), QPointF(17, 15))
            painter.drawLine(QPointF(9, 4), QPointF(10.5, 7))
            painter.drawLine(QPointF(15, 4), QPointF(13.5, 7))
        elif name == "rules":
            painter.drawRoundedRect(QRectF(5, 3, 14, 18), 2, 2)
            painter.drawLine(QPointF(8.5, 8), QPointF(15.5, 8))
            painter.drawLine(QPointF(8.5, 12), QPointF(15.5, 12))
            painter.drawLine(QPointF(8.5, 16), QPointF(13, 16))
        elif name == "update":
            painter.drawArc(QRectF(5, 5, 14, 14), 30 * 16, 290 * 16)
            painter.drawLine(QPointF(19, 5), QPointF(19, 9.5))
            painter.drawLine(QPointF(19, 9.5), QPointF(14.6, 9))
        elif name == "logout":
            painter.drawLine(QPointF(3, 12), QPointF(15, 12))
            painter.drawLine(QPointF(11, 8), QPointF(15, 12))
            painter.drawLine(QPointF(11, 16), QPointF(15, 12))
            painter.drawLine(QPointF(18, 4), QPointF(18, 20))
            painter.drawLine(QPointF(18, 4), QPointF(12, 4))
            painter.drawLine(QPointF(18, 20), QPointF(12, 20))
        elif name == "auth":
            painter.drawRoundedRect(QRectF(6, 10, 12, 10), 2, 2)
            painter.drawArc(QRectF(8, 4, 8, 12), 0, 180 * 16)
            painter.drawLine(QPointF(12, 14), QPointF(12, 17))
        return
    # Fallback: a neutral rounded square with a dot so no action is invisible.
    painter.drawRoundedRect(QRectF(4, 4, 16, 16), 4, 4)
    painter.setBrush(filled)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QRectF(9.5, 9.5, 5, 5))


@lru_cache(maxsize=512)
def _pixmap(name: str, color_name: str, size: int) -> QPixmap:
    color = QColor(color_name)
    render_size = max(16, int(size)) * 2
    pixmap = QPixmap(render_size, render_size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(render_size / 24.0, render_size / 24.0)
    _draw(name, painter, color)
    painter.end()
    pixmap.setDevicePixelRatio(2.0)
    return pixmap


def icon(name: str, role: str = "icon", size: int = 24) -> QIcon:
    theme = _theme()
    color = theme.color(role)
    return QIcon(_pixmap(name, color, int(size)))


def pixmap(name: str, role: str = "icon", size: int = 24) -> QPixmap:
    theme = _theme()
    return _pixmap(name, theme.color(role), int(size))


def logo_pixmap(size: int = 48, role: str = "accent") -> QPixmap:
    """Original neutral logo mark: rounded tile with the app initial."""

    theme = _theme()
    render_size = max(24, int(size)) * 2
    pixmap = QPixmap(render_size, render_size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(render_size / float(size), render_size / float(size))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(theme.qcolor(role))
    painter.drawRoundedRect(QRectF(0, 0, size, size), size * 0.28, size * 0.28)
    painter.setPen(theme.qcolor("on_accent"))
    font = QFont(theme.family("logo"))
    font.setWeight(QFont.Weight.Bold)
    font.setPixelSize(int(size * 0.58))
    painter.setFont(font)
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "A")
    painter.end()
    pixmap.setDevicePixelRatio(2.0)
    return pixmap


def icon_color(role: str) -> QColor:
    return _theme().qcolor(role)


# ThemeManager keeps a reference to the active instance for icon painting.
if not hasattr(ThemeManager, "_active"):
    ThemeManager._active = None  # type: ignore[attr-defined]
