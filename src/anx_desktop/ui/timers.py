"""Small timer helpers tied to a widget lifetime."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, QTimer


def single_shot(parent: QObject, msec: int, callback: Callable[[], None]) -> None:
    """Run ``callback`` once unless ``parent`` is destroyed first.

    ``QTimer.singleShot`` keeps a strong reference to a bound method/lambda, so
    a screen that is closed during the delay can be called after its C++ object
    is gone.  A timer parented to the widget is destroyed together with it.
    """

    timer = QTimer(parent)
    timer.setSingleShot(True)
    timer.timeout.connect(callback)
    timer.timeout.connect(timer.deleteLater)
    timer.start(max(0, int(msec)))
