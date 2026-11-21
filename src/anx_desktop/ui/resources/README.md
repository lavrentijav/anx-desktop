# UI resources

This directory is intentionally empty of copied assets.

- All icons are original neutral vector glyphs drawn at runtime in
  `anx_desktop/ui/icons.py` with `QPainter`.
- Posters, covers, avatars and screenshots are neutral gradient placeholders
  generated in `widgets/common.py` (`paint_placeholder`) so no Anixart artwork,
  icon, font or image from the APK is used.
- Typography uses system fonts with free fallbacks chosen by `ThemeManager`;
  no font files are bundled.
