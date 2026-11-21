import hashlib
import os

import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtMultimedia import QVideoFrame
from PySide6.QtWidgets import QApplication

from anx_desktop.ui import upscale
from anx_desktop.ui.upscale import UpscaleView, _fragments, _GRAPHS, _SHADERS


@pytest.fixture(scope='module')
def app():
    if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    return QApplication.instance() or QApplication([])


_SNAPSHOTS = [
    ('S', 5, '4c53ec2e287908f7ee7bcb266b0170421626d663576468b7d7dafc62962649a4'),
    ('M', 9, '716e02098a68f0d648761f2b96b4dd139e1cb09b174bb369fca3aa34328fff7e'),
    ('L', 10, 'db1fedf7be82f6fd9034e6bf39b64daf2b7576988bb584ec38f24f5236b1cd97'),
    ('VL', 18, '5638fe31c37c151a3443fea3451a3ef91af073f4dbb9615f6c0d1e29db11493d'),
    ('UL', 25, 'fa7cf0ecc1cca84d8291bbff5a42b60f5816d57b4e97d42bc377235ac8db02e8'),
]


@pytest.mark.parametrize(('model', 'layers', 'digest'), _SNAPSHOTS)
def test_upstream_snapshot(model, layers, digest):
    shader = _SHADERS[model]
    assert hashlib.sha256(shader.read_bytes()).hexdigest() == digest
    assert hashlib.sha256(shader.with_name('LICENSE').read_bytes()).hexdigest() == (
        '5bad448b737378e3d0c977ad0d0521fa37ad279a7e76ea9a31d9257eeb6953f5'
    )
    fragments = list(_fragments(shader.read_text(encoding='utf-8'), _GRAPHS[model]))
    assert len(fragments) == layers
    assert all('color = hook()' in fragment for fragment in fragments)


@pytest.mark.parametrize('mode', ['cpu', 'auto', 'opengl'])
def test_raster_fallback_keeps_frame_and_letterboxes(app, mode):
    view = UpscaleView(mode)
    changes = []
    view.backend_changed.connect(changes.append)
    frame = QImage(20, 10, QImage.Format.Format_RGB32)
    frame.fill(QColor('red'))
    view.video_sink.setVideoFrame(QVideoFrame(frame))
    view._use_cpu()
    view.resize(100, 100)
    view.show()
    app.processEvents()
    rendered = view.grab().toImage()
    assert rendered.pixelColor(50, 5) == QColor('black')
    assert rendered.pixelColor(50, 50) == QColor('red')
    assert changes == ['cpu']
    view.video_sink.setVideoFrame(QVideoFrame())
    assert view.grab().toImage().pixelColor(50, 50) == QColor('black')
    view.close()


@pytest.mark.parametrize(('model', 'layers'), [(model, layers) for model, layers, _ in _SNAPSHOTS])
@pytest.mark.parametrize(('passes', 'scale'), [(1, 1.5), (1, 2), (1, 4), (2, 3), (2, 4), (3, 4)])
def test_opengl_executes_cnn(app, model, layers, passes, scale):
    view = UpscaleView('opengl', model=model, passes=passes, scale=scale,
                       sharp=(model == "M" and passes == 2 and scale == 4))
    if view._gl is None:
        pytest.skip('Qt platform does not support QOpenGLWidget')
    surface = view._gl
    view.resize(64, 64)
    view.show()
    if not surface.isValid():
        view.close()
        pytest.skip('No Qt OpenGL context')
    draws = []
    draw_target = surface._draw_target

    def record(gl, fbo, program, bindings):
        draws.append((fbo.size().toTuple(), bindings))
        return draw_target(gl, fbo, program, bindings)

    surface._draw_target = record
    frame = QImage(32, 32, QImage.Format.Format_RGB32)
    frame.fill(QColor('black'))
    for y in range(16):
        for x in range(16):
            frame.setPixelColor(x, y, QColor('white'))
    view.video_sink.setVideoFrame(QVideoFrame(frame))
    cnn = surface.grabFramebuffer()
    app.processEvents()
    assert view._backend == 'opengl'
    expected = []
    for stage in range(passes):
        expected.extend([(32 * 2**stage,) * 2] * (layers - 1))
        expected.append((64 * 2**stage,) * 2)
    if scale != 2**passes:
        expected.append((int(32 * scale),) * 2)
    assert [size for size, _ in draws[:len(expected)]] == expected
    assert [fbo.size().toTuple() for fbo in surface._targets] == expected
    source = surface._texture.textureId()
    for stage in range(passes):
        textures = {'MAIN': source}
        for index, (output, names, _) in enumerate(_GRAPHS[model], start=stage * layers):
            assert draws[index][1] == [(f'{name}_sampler', textures[name]) for name in names]
            textures[output] = surface._targets[index].texture()
        source = textures['MAIN']
    if scale != 2**passes:
        assert draws[passes * layers][1] == [('frame', source)]
    assert cnn.pixelColor(8, 8).red() > 240
    assert cnn.pixelColor(8, 55).red() < 15
    # Bypass only the CNN, retaining the same GL upload and presentation path.
    surface._cnn = lambda gl, texture: texture
    linear = surface.grabFramebuffer()
    assert cnn != linear
    view.close()
    surface._cleanup()


@pytest.mark.parametrize('kwargs', [dict(model='XL'), dict(passes=0), dict(passes=True),
                                    dict(passes=4), dict(scale=2.5)])
def test_invalid_parameters(app, kwargs):
    with pytest.raises(ValueError):
        UpscaleView('cpu', **kwargs)


@pytest.mark.parametrize('limit', ['budget', 'texture'])
def test_gl_resource_limit_keeps_frame_in_raster(app, monkeypatch, limit):
    view = UpscaleView('opengl', model='M', passes=2, scale=3)
    surface = view._gl
    if surface is None:
        pytest.skip('Qt platform does not support QOpenGLWidget')
    view.resize(64, 64)
    view.show()
    if not surface.isValid():
        view.close()
        pytest.skip('No Qt OpenGL context')
    if limit == 'budget':
        monkeypatch.setattr(upscale, '_available_gpu_bytes', lambda *_: 1)
    else:
        surface._max_texture_size = 48  # Source fits, but even a single x2 pass does not.
    created = []
    monkeypatch.setattr(upscale, 'QOpenGLFramebufferObject', lambda *args: created.append(args))
    frame = QImage(32, 32, QImage.Format.Format_RGB32)
    frame.fill(QColor('red'))
    view.video_sink.setVideoFrame(QVideoFrame(frame))
    surface.grabFramebuffer()
    app.processEvents()
    assert not created
    assert view._backend == 'cpu'
    assert view.grab().toImage().pixelColor(32, 32) == QColor('red')
    view.close()


def test_gl_reports_reduced_pass_count(app):
    view = UpscaleView('opengl', model='M', passes=2, scale=2)
    surface = view._gl
    if surface is None:
        pytest.skip('Qt platform does not support QOpenGLWidget')
    view.resize(64, 64)
    view.show()
    try:
        if not surface.isValid():
            pytest.skip('No Qt OpenGL context')
        surface._max_texture_size = 64
        frame = QImage(32, 32, QImage.Format.Format_RGB32)
        frame.fill(QColor('red'))
        view.video_sink.setVideoFrame(QVideoFrame(frame))
        surface.grabFramebuffer()
        app.processEvents()
        assert view.effective_passes == 1
    finally:
        view.close()
