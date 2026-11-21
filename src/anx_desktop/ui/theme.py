"""Theme application: tokens -> QPalette + Qt stylesheet.

No literal colour appears below; every value comes from the canonical token
document.  Hover/pressed shades are derived from the accent by mixing with
text tokens, which keeps the palette bound to the 8.5.2 source.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

from .tokens import Tokens, tokens

_THEME_FAMILY_FALLBACKS = {
    "default": ["Inter", "Roboto", "Noto Sans", "DejaVu Sans", "Liberation Sans"],
    "toolbar_title": ["Inter", "Noto Sans", "DejaVu Sans", "Liberation Sans"],
    "section_title": ["Inter", "Roboto", "Noto Sans", "DejaVu Sans", "Liberation Sans"],
    "release_title": ["Inter", "Noto Sans", "DejaVu Sans", "Liberation Sans"],
    "logo": ["Varela Round", "Inter", "DejaVu Sans", "Liberation Sans"],
    "tab": ["Inter", "Roboto", "Noto Sans", "DejaVu Sans", "Liberation Sans"],
    "heavy": ["Inter", "Roboto", "Noto Sans", "DejaVu Sans", "Liberation Sans"],
    "numbers": ["Inter", "Roboto", "DejaVu Sans", "Liberation Sans"],
}


def mix(first: QColor, second: QColor, factor: float) -> QColor:
    """Linear mix, factor 0 -> first, 1 -> second."""

    factor = max(0.0, min(1.0, factor))
    return QColor(
        round(first.red() + (second.red() - first.red()) * factor),
        round(first.green() + (second.green() - first.green()) * factor),
        round(first.blue() + (second.blue() - first.blue()) * factor),
        round(first.alpha() + (second.alpha() - first.alpha()) * factor),
    )


def rgba(color: QColor, alpha: float | None = None) -> str:
    if alpha is None:
        alpha = color.alphaF()
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {max(0.0, min(1.0, alpha)):.3f})"


class ThemeManager(QObject):
    changed = Signal()
    palette_changed = Signal()
    _active: "ThemeManager | None" = None

    def __init__(self, app: QApplication | None, token_store: Tokens | None = None) -> None:
        super().__init__()
        ThemeManager._active = self
        self.app = app
        self.tokens = token_store or tokens()
        self._mode = "system"
        families = set(QFontDatabase.families())
        self._families: dict[str, str] = {}
        for key, candidates in _THEME_FAMILY_FALLBACKS.items():
            chosen = next((name for name in candidates if name in families), candidates[-1])
            self._families[key] = chosen
        self._resolved = "light"
        if app is not None:
            self._install_system_listener()

    # ------------------------------------------------------------------ state
    @property
    def mode(self) -> str:
        return self._mode

    @property
    def resolved(self) -> str:
        return self._resolved

    @property
    def dark(self) -> bool:
        return self._resolved == "dark"

    def _system_dark(self) -> bool:
        if self.app is None:
            return False
        try:
            scheme = self.app.styleHints().colorScheme()
            return scheme == Qt.ColorScheme.Dark
        except Exception:
            return False

    def _install_system_listener(self) -> None:
        try:
            self.app.styleHints().colorSchemeChanged.connect(self._on_system_scheme)
        except Exception:
            pass

    def _on_system_scheme(self, _scheme: object) -> None:
        if self._mode == "system":
            self.apply(self._mode)

    def set_mode(self, mode: str) -> None:
        normalized = mode if mode in {"light", "dark", "system"} else "system"
        if normalized == self._mode:
            # Re-apply on demand (e.g. accent icons after manual change).
            self.apply(normalized)
            return
        self.apply(normalized)

    def apply(self, mode: str | None = None) -> None:
        if mode is not None:
            self._mode = mode if mode in {"light", "dark", "system"} else "system"
        self._resolved = "dark" if (
            self._mode == "dark" or (self._mode == "system" and self._system_dark())
        ) else "light"
        if self.app is None:
            return
        self.app.setStyle("Fusion")
        self._apply_palette()
        font = self.font("body")
        self.app.setFont(font)
        self.app.setStyleSheet(self.build_qss())
        self.changed.emit()
        self.palette_changed.emit()

    # --------------------------------------------------------------- accessors
    def color(self, role: str) -> str:
        return self.tokens.color(role, self._resolved)

    def qcolor(self, role: str) -> QColor:
        return QColor(self.color(role))

    def alpha_color(self, role: str, alpha: float | None = None) -> str:
        return rgba(self.qcolor(role), alpha)

    def mix_color(self, role_a: str, role_b: str, factor: float) -> str:
        return mix(self.qcolor(role_a), self.qcolor(role_b), factor).name(QColor.NameFormat.HexArgb)

    def px(self, value: float) -> int:
        """Token dp -> desktop logical px.

        Qt itself applies the OS scale factor to logical px, so the token value
        is used as-is (1 dp = 1 px at 100%).  Sub-pixel hairlines become 1 px.
        """

        if value <= 0:
            return 0
        if value < 1:
            return 1
        return int(round(value))

    def space(self, name: str) -> int:
        return self.px(self.tokens.space(name))

    def semantic(self, name: str) -> int:
        return self.px(self.tokens.semantic(name))

    def radius(self, name: str) -> int:
        return self.px(self.tokens.radius(name))

    def layout(self, name: str) -> int:
        return self.px(float(self.tokens.layout(name)))

    def desktop(self, name: str) -> int:
        return self.tokens.desktop(name)

    def family(self, key: str = "default") -> str:
        return self._families.get(key, self._families["default"])

    def font(self, scale_name: str = "body", *, family_key: str | None = None,
             point_delta: float = 0.0, bold: bool | None = None) -> QFont:
        spec = self.tokens.typography(scale_name)
        family = self.family(family_key or str(spec.get("family", "default")))
        font = QFont(family)
        size_sp = float(spec.get("size_sp", 14)) + point_delta
        # Qt point size on a 96-dpi desktop maps closely to Android sp.
        font.setPointSizeF(max(7.0, size_sp * 0.75))
        weight = spec.get("weight", "regular")
        if bold is True or weight in {"bold", "black"}:
            font.setWeight(QFont.Weight.Bold)
        elif weight == "medium":
            font.setWeight(QFont.Weight.Medium)
        else:
            font.setWeight(QFont.Weight.Normal)
        if spec.get("text_transform") == "uppercase":
            font.setCapitalization(QFont.Capitalization.AllUppercase)
        return font

    # ----------------------------------------------------------------- palette
    def _apply_palette(self) -> None:
        palette = QPalette()
        background = self.qcolor("background")
        surface = self.qcolor("surface")
        text = self.qcolor("text_primary")
        muted = self.qcolor("text_secondary")
        accent = self.qcolor("accent")
        on_accent = self.qcolor("on_accent")
        palette.setColor(QPalette.ColorRole.Window, background)
        palette.setColor(QPalette.ColorRole.WindowText, text)
        palette.setColor(QPalette.ColorRole.Base, surface)
        palette.setColor(QPalette.ColorRole.AlternateBase, self.qcolor("surface_tertiary"))
        palette.setColor(QPalette.ColorRole.Text, text)
        palette.setColor(QPalette.ColorRole.PlaceholderText, self.qcolor("text_tertiary"))
        palette.setColor(QPalette.ColorRole.Button, surface)
        palette.setColor(QPalette.ColorRole.ButtonText, text)
        palette.setColor(QPalette.ColorRole.BrightText, on_accent)
        palette.setColor(QPalette.ColorRole.Highlight, accent)
        palette.setColor(QPalette.ColorRole.HighlightedText, on_accent)
        palette.setColor(QPalette.ColorRole.ToolTipBase, self.qcolor("tooltip_background"))
        palette.setColor(QPalette.ColorRole.ToolTipText, self.qcolor("tooltip_text"))
        palette.setColor(QPalette.ColorRole.Link, self.qcolor("text_link"))
        palette.setColor(QPalette.ColorRole.LinkVisited, self.qcolor("text_link"))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, muted)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, muted)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, muted)
        if self.app is not None:
            self.app.setPalette(palette)

    # --------------------------------------------------------------------- QSS
    def build_qss(self) -> str:
        c = self.color
        px = self.px
        r = self.radius
        family = self.family("default")
        heading = self.family("section_title")
        logo = self.family("logo")
        accent = QColor(c("accent"))
        text = QColor(c("text_primary"))
        ripple = QColor(c("ripple"))
        hover = mix(accent, text, 0.12).name()
        pressed = mix(accent, text, 0.22).name()
        soft_hover = rgba(mix(text, accent, 0.18), 0.10)
        soft_pressed = rgba(accent, 0.16)
        border = c("border")
        border_soft = c("border_soft")
        bg = c("background")
        surface = c("surface")
        surface_secondary = c("surface_secondary")
        surface_tertiary = c("surface_tertiary")
        primary_text = c("text_primary")
        secondary_text = c("text_secondary")
        tertiary_text = c("text_tertiary")
        icon = c("icon")
        menu_bg = c("menu_background")
        dialog_bg = c("dialog_background")
        accent_text = c("text_link")
        on_accent = c("on_accent")
        error = c("danger")
        success = c("success")
        warning = c("warning")
        switch_outline = c("switch_outline")
        input_radius = r("tag")
        button_radius = r("button")
        tag_radius = r("tag")
        dialog_radius = r("dialog")
        card_radius = r("collection_card")
        chip_outline = c("chip_outline")
        chip_selected = c("chip_selected_background")
        chip_unselected = c("chip_unselected_background")
        return f"""
        QWidget {{
            font-family: "{family}";
            font-size: {px(14)}px;
            color: {primary_text};
            selection-background-color: {c("accent_soft_20")};
            selection-color: {primary_text};
        }}
        QMainWindow, QDialog {{
            background-color: {bg};
        }}
        QWidget[ui="appRoot"], QWidget[ui="screen"], QWidget[ui="scrollHost"] {{
            background-color: {bg};
        }}
        QLabel {{
            background: transparent;
            color: {primary_text};
        }}
        QLabel[role="muted"] {{ color: {secondary_text}; }}
        QLabel[role="tertiary"] {{ color: {tertiary_text}; }}
        QLabel[role="accent"] {{ color: {accent_text}; }}
        QLabel[role="danger"] {{ color: {error}; }}
        QLabel[role="success"] {{ color: {success}; }}
        QLabel[role="warning"] {{ color: {warning}; }}
        QLabel[role="title"] {{
            font-family: "{heading}";
            font-size: {px(20)}px;
            font-weight: 600;
            color: {primary_text};
        }}
        QLabel[role="section"] {{
            font-family: "{heading}";
            font-size: {px(18)}px;
            font-weight: 600;
            color: {primary_text};
        }}
        QLabel[role="logo"] {{
            font-family: "{logo}";
            font-size: {px(24)}px;
            font-weight: 700;
            color: {primary_text};
        }}
        QLabel[role="caption"] {{
            font-size: {px(11)}px;
            color: {tertiary_text};
        }}
        QLabel[role="uppercase"] {{
            font-family: "{heading}";
            font-size: {px(13)}px;
            font-weight: 600;
            color: {secondary_text};
            letter-spacing: 1px;
        }}
        QFrame[ui="topBar"] {{
            background-color: {bg};
            border-bottom: 1px solid {border};
        }}
        QFrame[ui="sidebar"] {{
            background-color: {surface_secondary};
            border-right: 1px solid {border};
        }}
        QFrame[ui="divider"] {{
            background-color: {border_soft};
            border: none;
        }}
        QFrame[ui="card"] {{
            background-color: {surface};
            border: 1px solid {border_soft};
            border-radius: {card_radius}px;
        }}
        QFrame[ui="panel"] {{
            background-color: {surface_secondary};
            border: 1px solid {border_soft};
            border-radius: {card_radius}px;
        }}
        QFrame[ui="tertiary"] {{
            background-color: {surface_tertiary};
            border: none;
            border-radius: {input_radius}px;
        }}
        QFrame[ui="accentSoft"] {{
            background-color: {c("accent_soft_10")};
            border: none;
            border-radius: {input_radius}px;
        }}
        QFrame[ui="info"] {{
            background-color: {c("info_background")};
            border: 1px solid {border_soft};
            border-radius: {r("info_box")}px;
        }}
        QFrame[ui="dangerSoft"] {{
            background-color: {c("accent_soft_10")};
            border: 1px solid {error};
            border-radius: {input_radius}px;
        }}
        QFrame[ui="skeleton"] {{
            background-color: {surface_tertiary};
            border-radius: {input_radius}px;
        }}
        QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background-color: {surface_secondary};
            color: {primary_text};
            border: 1px solid {border};
            border-radius: {input_radius}px;
            padding: {px(8)}px {px(12)}px;
            min-height: {px(32)}px;
        }}
        QLineEdit:hover, QComboBox:hover, QPlainTextEdit:hover, QTextEdit:hover {{
            border-color: {c("icon_secondary")};
        }}
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus {{
            border: 1px solid {accent_text};
        }}
        QLineEdit[ui="search"] {{
            background-color: {surface_secondary};
            border: 1px solid {border_soft};
            border-radius: {px(21)}px;
            padding: 0 {px(16)}px;
            min-height: {px(32)}px;
            max-height: {px(42)}px;
        }}
        QLineEdit[ui="search"]:focus {{
            border: 1px solid {accent_text};
        }}
        QLineEdit[ui="error"], QComboBox[ui="error"] {{
            border: 1px solid {error};
        }}
        QPlainTextEdit[ui="comment"] {{
            background-color: {surface_tertiary};
            border: none;
            border-radius: {input_radius}px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: {px(28)}px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {menu_bg};
            color: {primary_text};
            border: 1px solid {border};
            selection-background-color: {c("accent_soft_10")};
            selection-color: {primary_text};
            padding: {px(4)}px;
            outline: none;
        }}
        QPushButton {{
            background-color: transparent;
            color: {primary_text};
            border: none;
            border-radius: {button_radius}px;
            padding: {px(8)}px {px(16)}px;
            min-height: {px(32)}px;
            font-family: "{heading}";
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {soft_hover};
        }}
        QPushButton:pressed {{
            background-color: {soft_pressed};
        }}
        QPushButton:disabled {{
            color: {tertiary_text};
        }}
        QPushButton[ui="primary"] {{
            background-color: {c("accent")};
            color: {on_accent};
            border-radius: {button_radius}px;
            padding: {px(10)}px {px(20)}px;
            min-height: {px(40)}px;
        }}
        QPushButton[ui="primary"]:hover {{ background-color: {hover}; }}
        QPushButton[ui="primary"]:pressed {{ background-color: {pressed}; }}
        QPushButton[ui="primary"]:disabled {{
            background-color: {c("accent_soft_50")};
            color: {tertiary_text};
        }}
        QPushButton[ui="outlined"] {{
            background-color: transparent;
            color: {primary_text};
            border: 1px solid {border};
            border-radius: {button_radius}px;
            padding: {px(10)}px {px(20)}px;
            min-height: {px(40)}px;
        }}
        QPushButton[ui="outlined"]:hover {{ background-color: {soft_hover}; }}
        QPushButton[ui="outlined"]:pressed {{ background-color: {soft_pressed}; }}
        QPushButton[ui="text"] {{
            background: transparent;
            color: {accent_text};
            border: none;
            padding: {px(8)}px;
            min-height: {px(28)}px;
        }}
        QPushButton[ui="text"]:hover {{ background-color: {soft_hover}; }}
        QPushButton[ui="grey"] {{
            background-color: {c("secondary_button")};
            color: {c("secondary_button_text")};
            border-radius: {button_radius}px;
            padding: {px(8)}px {px(16)}px;
            min-height: {px(36)}px;
        }}
        QPushButton[ui="danger"] {{
            background-color: {c("delete_button")};
            color: {c("delete_button_text")};
            border-radius: {button_radius}px;
            padding: {px(8)}px {px(16)}px;
            min-height: {px(36)}px;
        }}
        QPushButton[ui="tag"], QPushButton[ui="chip"] {{
            background-color: {chip_unselected};
            color: {secondary_text};
            border: 1px solid {chip_outline};
            border-radius: {tag_radius}px;
            padding: {px(6)}px {px(16)}px;
            min-height: {px(24)}px;
            font-weight: 400;
        }}
        QPushButton[ui="tag"]:hover, QPushButton[ui="chip"]:hover {{
            background-color: {surface_tertiary};
        }}
        QPushButton[ui="chip"]:checked {{
            background-color: {chip_selected};
            color: {primary_text};
            border: 1px solid transparent;
        }}
        QPushButton[ui="tab"] {{
            background: transparent;
            color: {secondary_text};
            border: none;
            border-radius: 0;
            padding: {px(6)}px {px(16)}px;
            min-height: 0;
            font-family: "{family}";
            font-weight: 400;
        }}
        QPushButton[ui="tab"]:hover {{
            color: {primary_text};
            background-color: {soft_hover};
        }}
        QPushButton[ui="tab"]:checked {{
            color: {primary_text};
            background: transparent;
        }}
        QPushButton[ui="tab"]:checked:hover {{
            background-color: {soft_hover};
        }}
        QPushButton[ui="segmented"] {{
            background-color: transparent;
            color: {secondary_text};
            border: 1px solid {border};
            border-radius: {tag_radius}px;
            padding: {px(6)}px {px(14)}px;
            min-height: {px(24)}px;
        }}
        QPushButton[ui="segmented"]:checked {{
            background-color: {c("accent_soft_10")};
            color: {primary_text};
            border-color: {accent_text};
        }}
        QPushButton[ui="icon"] {{
            background: transparent;
            border: none;
            border-radius: {r("button_circle")}px;
            padding: {px(6)}px;
            min-width: {px(32)}px;
            min-height: {px(32)}px;
        }}
        QPushButton[ui="icon"]:hover {{ background-color: {soft_hover}; }}
        QPushButton[ui="icon"]:checked {{
            background-color: {c("accent_soft_10")};
        }}
        QToolButton {{
            background: transparent;
            border: none;
            border-radius: {r("button_circle")}px;
            padding: {px(6)}px;
            color: {icon};
        }}
        QToolButton:hover {{ background-color: {soft_hover}; }}
        QToolButton:pressed {{ background-color: {soft_pressed}; }}
        QToolButton:checked {{ background-color: {c("accent_soft_10")}; }}
        QToolButton[ui="nav"] {{
            background: transparent;
            color: {secondary_text};
            border: none;
            border-radius: {input_radius}px;
            padding: {px(8)}px {px(12)}px;
            text-align: left;
            min-height: {px(36)}px;
        }}
        QToolButton[ui="nav"]:hover {{ background-color: {soft_hover}; color: {primary_text}; }}
        QToolButton[ui="nav"]:checked {{
            background-color: {c("nav_indicator")};
            color: {c("nav_label_active")};
            font-weight: 600;
        }}
        QToolButton[ui="navCompact"] {{
            background: transparent;
            border: none;
            border-radius: {input_radius}px;
            min-width: {px(40)}px;
            min-height: {px(40)}px;
        }}
        QToolButton[ui="navCompact"]:hover {{ background-color: {soft_hover}; }}
        QToolButton[ui="navCompact"]:checked {{
            background-color: {c("nav_indicator")};
        }}
        QPushButton[ui="nav"] {{
            background: transparent;
            color: {secondary_text};
            border: none;
            border-radius: {input_radius}px;
            padding: {px(8)}px {px(12)}px;
            text-align: left;
            min-height: {px(34)}px;
            font-family: "{family}";
            font-weight: 400;
        }}
        QPushButton[ui="nav"]:hover {{ background-color: {soft_hover}; color: {primary_text}; }}
        QPushButton[ui="nav"]:checked {{
            background-color: {c("nav_indicator")};
            color: {c("nav_label_active")};
            font-weight: 600;
        }}
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: {px(10)}px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {c("separator")};
            border-radius: {px(5)}px;
            min-height: {px(28)}px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {c("text_tertiary")}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
            height: 0;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: {px(10)}px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {c("separator")};
            border-radius: {px(5)}px;
            min-width: {px(28)}px;
        }}
        QScrollBar::handle:horizontal:hover {{ background: {c("text_tertiary")}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: transparent;
            width: 0;
        }}
        QMenu {{
            background-color: {menu_bg};
            color: {primary_text};
            border: 1px solid {border};
            border-radius: {dialog_radius}px;
            padding: {px(8)}px;
        }}
        QMenu::item {{
            padding: {px(8)}px {px(24)}px {px(8)}px {px(12)}px;
            border-radius: {input_radius}px;
            background: transparent;
        }}
        QMenu::item:selected {{
            background-color: {c("accent_soft_10")};
            color: {primary_text};
        }}
        QMenu::separator {{
            height: 1px;
            background: {border_soft};
            margin: {px(6)}px {px(8)}px;
        }}
        QDialog {{
            background-color: {dialog_bg};
        }}
        QDialog QLabel {{
            background: transparent;
        }}
        QToolTip {{
            background-color: {c("tooltip_background")};
            color: {c("tooltip_text")};
            border: none;
            border-radius: {r("small_badge")}px;
            padding: {px(6)}px {px(12)}px;
        }}
        QProgressBar {{
            background-color: {c("progress_track")};
            border: none;
            border-radius: {r("progress_track")}px;
            min-height: {px(6)}px;
            max-height: {px(10)}px;
            text-align: center;
            color: transparent;
        }}
        QProgressBar::chunk {{
            background-color: {c("progress_indicator")};
            border-radius: {r("progress_track")}px;
        }}
        QSlider::groove:horizontal {{
            background: {c("progress_track")};
            height: {px(2)}px;
            border-radius: {px(1)}px;
        }}
        QSlider::sub-page:horizontal {{
            background: {c("progress_indicator")};
            height: {px(2)}px;
            border-radius: {px(1)}px;
        }}
        QSlider::handle:horizontal {{
            background: {c("progress_indicator")};
            width: {px(12)}px;
            height: {px(12)}px;
            margin: {px(-5)}px 0;
            border-radius: {px(6)}px;
        }}
        QSlider[ui="player"]::groove:horizontal {{
            background: {c("player_scrim")};
            height: {px(2)}px;
        }}
        QSlider[ui="player"]::sub-page:horizontal {{
            background: {accent_text};
        }}
        QSlider[ui="player"]::handle:horizontal {{
            background: {accent_text};
            width: {px(12)}px;
            height: {px(12)}px;
            margin: {px(-5)}px 0;
            border-radius: {px(6)}px;
        }}
        QCheckBox, QRadioButton {{
            background: transparent;
            spacing: {px(8)}px;
            color: {primary_text};
        }}
        QCheckBox::indicator, QRadioButton::indicator {{
            width: {px(18)}px;
            height: {px(18)}px;
            border: 2px solid {chip_outline};
            background: {surface_secondary};
        }}
        QCheckBox::indicator {{ border-radius: {px(4)}px; }}
        QRadioButton::indicator {{ border-radius: {px(9)}px; }}
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
            background: {accent_text};
            border-color: {accent_text};
        }}
        QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
            border-color: {accent_text};
        }}
        QSplitter::handle {{
            background: {border_soft};
        }}
        QSplitter::handle:horizontal {{ width: 1px; }}
        QSplitter::handle:vertical {{ height: 1px; }}
        QStatusBar {{
            background: {bg};
            color: {secondary_text};
            border-top: 1px solid {border_soft};
        }}
        QAbstractItemView {{
            background: {surface};
            color: {primary_text};
            border: 1px solid {border_soft};
            selection-background-color: {c("accent_soft_10")};
            selection-color: {primary_text};
            outline: none;
        }}
        QHeaderView::section {{
            background: {surface_secondary};
            color: {secondary_text};
            border: none;
            border-bottom: 1px solid {border_soft};
            padding: {px(6)}px {px(8)}px;
        }}
        QListWidget, QListView, QTreeView, QTableView {{
            background: transparent;
            border: none;
        }}
        QToolBar {{
            background: transparent;
            border: none;
            spacing: {px(4)}px;
        }}
        QTabWidget::pane {{
            border: none;
        }}
        QTabBar::tab {{
            background: transparent;
            color: {secondary_text};
            padding: {px(8)}px {px(12)}px;
            border-bottom: 3px solid transparent;
        }}
        QTabBar::tab:selected {{
            color: {primary_text};
            border-bottom: 3px solid {accent_text};
        }}
        QMessageBox {{
            background-color: {dialog_bg};
        }}
        """


def active_theme() -> ThemeManager:
    """Return the application-wide theme manager."""

    manager = ThemeManager._active
    if manager is None:  # pragma: no cover - only before app bootstrap
        raise RuntimeError("ThemeManager is not initialised")
    return manager
