# anx-desktop

Unofficial desktop anime client. This project is not affiliated with or endorsed by the service it connects to.

## Layout

- `src/anx_desktop/` — Python UI application (PySide6)
- `docs/` — clean-room specifications (API, UI style)
- `tasks/` — subagent tasks for the clean-room pipeline
- `api/references/` — local APK dumps and analysis, ignored by git
- `api/references/apk/` — reference APKs (11-beta-2 and 8-5-2)

## Run

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
python -m anx_desktop
```

## Linux release candidate (Nuitka)

Use Python 3.12, a C compiler, and the system libraries required by Qt for
X11 or Wayland. Activate the virtual environment before building so `patchelf`
is on `PATH`.

```sh
python -m pip install -e '.[dev,release]'
QT_QPA_PLATFORM=offscreen python -m pytest -q
PYTHONPATH=src python -m nuitka --mode=standalone --enable-plugin=pyside6 \
    --include-qt-plugins=sensible,multimedia \
    --include-data-files=src/anx_desktop/ui/resources/ui-8.5-tokens.json=anx_desktop/ui/resources/ui-8.5-tokens.json \
    --include-data-dir=src/anx_desktop/ui/resources/anime4k=anx_desktop/ui/resources/anime4k \
    --nofollow-import-to=anx_desktop.api.antitamper \
    --output-dir=dist --output-filename=anx-desktop --jobs=3 \
    src/anx_desktop/__main__.py
QT_QPA_PLATFORM=offscreen dist/__main__.dist/anx-desktop --smoke-test
```

Distribute the entire `dist/__main__.dist/` directory, not just the executable.
Install `ffmpeg` to run the local MP4 playback regression test. Before publishing,
check the bundle on the target Linux distribution, then verify sign-in, episode
selection and actual playback with a provider you are authorized to use. The UI
smoke test uses demo data and does not verify live API or provider access. The
bundle deliberately excludes the untracked local anti-tamper module; API
features that require its headers may be unavailable.

See `tasks/README.md` for the dirty-room / clean-room workflow.
