"""Qt video presentation using the upstream Anime4K RGB CNN x2 (S/M/L/VL/UL)."""

import logging
from pathlib import Path

from PySide6.QtCore import QRectF, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QSurfaceFormat
from PySide6.QtMultimedia import QVideoFrame, QVideoSink
from PySide6.QtOpenGL import (
    QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat, QOpenGLShader,
    QOpenGLShaderProgram, QOpenGLTexture, QOpenGLVertexArrayObject,
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QStackedLayout, QWidget

_LOG = logging.getLogger(__name__)
_RESOURCES = Path(__file__).with_name('resources') / 'anime4k'
_SHADERS = {model: _RESOURCES / f'Anime4K_Upscale_CNN_x2_{model}.glsl'
            for model in ('S', 'M', 'L', 'VL', 'UL')}
_SHADER = _SHADERS['S']
def _available_gpu_bytes(context, gl):
    # NVX exposes a scalar estimate; there is no portable OpenGL equivalent.
    if context.hasExtension(b'GL_NVX_gpu_memory_info'):
        kib = gl.glGetIntegerv(0x9049)  # GL_GPU_MEMORY_INFO_CURRENT_AVAILABLE_VIDMEM_NVX
        if isinstance(kib, int) and kib > 0:
            return kib * 1024
    return None



def _graph(features, planes=1, output_planes=1, skip_from=-1):
    def group(name, count):
        return (name, *(f'{name}{i}' for i in range(1, count)))

    names = [group('conv2d_tf' if i == 0 else f'conv2d_{i}_tf', planes)
             for i in range(features)]
    graph = [(out, inputs, 1)
             for inputs, outputs in zip([('MAIN',), *names], names)
             for out in outputs]
    tail = group('conv2d_last_tf', output_planes)
    tail_inputs = tuple(name for group_names in names[skip_from:] for name in group_names)
    graph.extend((out, tail_inputs, 1) for out in tail)
    graph.append(('MAIN', ('MAIN', *tail), 2))
    return graph


_GRAPHS = {
    'S': _graph(3),
    'M': _graph(7, skip_from=0),
    'L': _graph(3, planes=2, output_planes=3),
    'VL': _graph(7, planes=2, output_planes=3, skip_from=0),
    'UL': _graph(7, planes=3, output_planes=3, skip_from=2),
}
_VERTEX = '''#version 330 core
out vec2 uv;
void main() {
    uv = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    gl_Position = vec4(uv * 2.0 - 1.0, 0.0, 1.0);
}
'''
_HEADER = '#version 330 core\nin vec2 uv;\nout vec4 color;\n'
_PRESENT = _HEADER + '''uniform sampler2D frame;
void main() { color = vec4(texture(frame, vec2(uv.x, 1.0 - uv.y)).rgb, 1.0); }
'''


# Apply bounded luma sharpening at presentation, without another framebuffer.
_PRESENT_SHARP = _HEADER + """uniform sampler2D frame;
float luma(vec3 c) { return dot(c, vec3(0.2126, 0.7152, 0.0722)); }
void main() {
    vec2 p = vec2(uv.x, 1.0 - uv.y);
    vec2 step = max(fwidth(p), 1.0 / vec2(textureSize(frame, 0)));
    vec3 c = texture(frame, p).rgb;
    float y = luma(c);
    float a = luma(texture(frame, p + vec2(step.x, 0)).rgb);
    float b = luma(texture(frame, p - vec2(step.x, 0)).rgb);
    float d = luma(texture(frame, p + vec2(0, step.y)).rgb);
    float e = luma(texture(frame, p - vec2(0, step.y)).rgb);
    float lo = min(y, min(min(a,b), min(d,e)));
    float hi = max(y, max(max(a,b), max(d,e)));
    float detail = clamp(0.28 * (y - (a+b+d+e)*0.25), -0.035, 0.035);
    color = vec4(clamp(c + vec3(clamp(y+detail, lo, hi)-y), 0.0, 1.0), 1.0);
}
"""


_RESAMPLE = _HEADER + """uniform sampler2D frame;
void main() { color = vec4(texture(frame, uv).rgb, 1.0); }
"""


def _fragments(source, graph=_GRAPHS['S']):
    """Supply the mpv hook variables for the pinned pass graphs."""
    passes = source.split('//!DESC ')[1:]
    if len(passes) != len(graph):
        raise ValueError('Unexpected Anime4K pass count')
    for body, (output, bindings, factor) in zip(passes, graph):
        lines = body.splitlines()
        if tuple(s[8:] for s in lines if s.startswith('//!BIND ')) != bindings:
            raise ValueError('Unexpected Anime4K bindings')
        # Depth-to-space doubles the first residual plane, not MAIN or the last plane.
        size_source = bindings[1] if factor == 2 else bindings[0]
        suffix = ' 2 *' if factor == 2 else ''
        if not all(line in lines for line in (f'//!SAVE {output}',
                f'//!WIDTH {size_source}.w{suffix}', f'//!HEIGHT {size_source}.h{suffix}')):
            raise ValueError('Unexpected Anime4K output')
        preamble = _HEADER
        for name in bindings:
            preamble += f'''uniform sampler2D {name}_sampler;
#define {name}_pos uv
#define {name}_size vec2(textureSize({name}_sampler, 0))
#define {name}_pt (1.0 / {name}_size)
#define {name}_tex(p) texture({name}_sampler, (p))
#define {name}_texOff(o) {name}_tex(uv + (o) * {name}_pt)
'''
        yield preamble + body[body.index('\n'):] + '\nvoid main() { color = hook(); }\n'


def _target_sizes(width, height, graph, passes, scale):
    sizes = [(width * factor * 2**stage, height * factor * 2**stage)
             for stage in range(passes) for _, _, factor in graph]
    if scale != 2**passes:
        sizes.append((int(width * scale + 0.5), int(height * scale + 0.5)))
    return sizes


def _fit(width, height, image):
    scale = min(width / image.width(), height / image.height())
    w, h = image.width() * scale, image.height() * scale
    return QRectF((width - w) / 2, (height - h) / 2, w, h)


class _RasterSurface(QWidget):
    image = QImage()

    def paintEvent(self, event):
        with QPainter(self) as painter:
            painter.fillRect(self.rect(), Qt.GlobalColor.black)
            if not self.image.isNull():
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                painter.drawImage(_fit(self.width(), self.height(), self.image),
                                  self.image, QRectF(self.image.rect()))


class _GLSurface(QOpenGLWidget):
    ready = Signal()
    failed = Signal()
    image = QImage()

    def __init__(self, parent, model, passes, scale, sharp=False):
        super().__init__(parent)
        fmt = QSurfaceFormat()
        fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        self.setFormat(fmt)
        self._sharp = sharp
        self._model = model
        self._graph = _GRAPHS[model]
        self._passes = passes
        self.effective_passes = passes
        self._scale = scale
        self._source_size = None
        self._failed = False
        self._ready = None
        self._programs = []
        self._targets = []
        self._vao = self._texture = None
        self._uploaded = None

    def _fail(self):
        self._failed = True
        _LOG.warning('Anime4K OpenGL unavailable; using Qt raster scaling', exc_info=True)
        self.failed.emit()

    def initializeGL(self):
        try:
            ctx = self.context()
            ctx.aboutToBeDestroyed.connect(self._cleanup)
            if ctx.isOpenGLES() or (ctx.format().majorVersion(), ctx.format().minorVersion()) < (3, 3):
                raise RuntimeError('Anime4K requires desktop OpenGL 3.3')
            self._vao = QOpenGLVertexArrayObject(self)
            if not self._vao.create():
                raise RuntimeError('Cannot create OpenGL VAO')
            gl = ctx.functions()
            self._max_texture_size = gl.glGetIntegerv(0x0D33)  # GL_MAX_TEXTURE_SIZE
            source = _SHADERS[self._model].read_text(encoding='utf-8')
            for fragment in (*_fragments(source, self._graph), _RESAMPLE, _PRESENT_SHARP if self._sharp else _PRESENT):
                program = QOpenGLShaderProgram()
                if not (program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, _VERTEX)
                        and program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, fragment)
                        and program.link()):
                    raise RuntimeError(program.log())
                self._programs.append(program)
        except (OSError, ValueError, TypeError, RuntimeError):
            self._fail()

    def _cleanup(self):
        self.makeCurrent()
        self._texture = None
        self._uploaded = None
        self._targets.clear()
        self._source_size = None
        self._programs.clear()
        if self._vao is not None:
            self._vao.destroy()
            self._vao = None
        self.doneCurrent()

    def _draw_pass(self, gl, program, bindings):
        if not program.bind():
            raise RuntimeError(program.log())
        for unit, (uniform, texture) in enumerate(bindings):
            gl.glActiveTexture(0x84C0 + unit)  # GL_TEXTURE0 + unit
            gl.glBindTexture(0x0DE1, texture)  # GL_TEXTURE_2D
            program.setUniformValue(program.uniformLocation(uniform), unit)
        gl.glDrawArrays(0x0004, 0, 3)  # GL_TRIANGLES
        program.release()
        gl.glActiveTexture(0x84C0)

    def _allocate_targets(self, gl, width, height):
        if self._source_size == (width, height):
            return
        self._texture = self._uploaded = None
        self._targets.clear()
        available = _available_gpu_bytes(self.context(), gl)
        fmt = QOpenGLFramebufferObjectFormat()
        fmt.setInternalTextureFormat(0x881A)  # GL_RGBA16F: signed CNN activations
        for passes in range(self._passes, 0, -1):
            sizes = _target_sizes(width, height, self._graph, passes, self._scale)
            estimated_bytes = 4 * width * height + 8 * sum(w * h for w, h in sizes)
            if any(max(w, h) > self._max_texture_size for w, h in sizes):
                continue
            if available is not None and estimated_bytes > available:
                continue
            for w, h in sizes:
                fbo = QOpenGLFramebufferObject(w, h, fmt)
                error = gl.glGetError()
                if not fbo.isValid() or error:
                    _LOG.warning('Anime4K framebuffer allocation failed (%dx%d, GL error %#x)', w, h, error)
                    del fbo
                    self._targets.clear()
                    break
                gl.glBindTexture(0x0DE1, fbo.texture())
                for pname, value in ((0x2801, 0x2601), (0x2800, 0x2601),
                                     (0x2802, 0x812F), (0x2803, 0x812F)):
                    gl.glTexParameteri(0x0DE1, pname, value)
                self._targets.append(fbo)
            else:
                self.effective_passes = passes
                self._source_size = (width, height)
                return
        raise RuntimeError(f'Anime4K resource limit for {width}x{height} '
                           f'({self._model}, {self._passes} CNN, scale {self._scale})')

    def _draw_target(self, gl, fbo, program, bindings):
        if not fbo.bind():
            raise RuntimeError('Cannot bind Anime4K framebuffer')
        gl.glViewport(0, 0, fbo.width(), fbo.height())
        self._draw_pass(gl, program, bindings)
        return fbo.texture()

    def _cnn(self, gl, source):
        layers = len(self._graph)
        for stage in range(self.effective_passes):
            inputs = {'MAIN': source}
            for index, (output, bindings, _) in enumerate(self._graph):
                inputs[output] = self._draw_target(
                    gl, self._targets[stage * layers + index], self._programs[index],
                    [(name + '_sampler', inputs[name]) for name in bindings])
            source = inputs['MAIN']
        if len(self._targets) > layers * self.effective_passes:
            source = self._draw_target(gl, self._targets[-1], self._programs[-2],
                                       [('frame', source)])
        return source

    def paintGL(self):
        if self._failed:
            return
        gl = self.context().functions()
        try:
            self._paint(gl)
        except (RuntimeError, TypeError, ValueError):
            self._fail()
        finally:
            gl.glBindFramebuffer(0x8D40, self.defaultFramebufferObject())

    def _paint(self, gl):
        dpr = self.devicePixelRatioF()
        width, height = round(self.width() * dpr), round(self.height() * dpr)
        gl.glDisable(0x0BE2)  # GL_BLEND
        gl.glDisable(0x0C11)  # GL_SCISSOR_TEST
        gl.glClearColor(0., 0., 0., 1.)
        gl.glClear(0x4000)  # GL_COLOR_BUFFER_BIT
        if self.image.isNull() or not width or not height:
            return
        self._allocate_targets(gl, self.image.width(), self.image.height())
        if self._uploaded is not self.image:
            self._texture = None
            self._texture = QOpenGLTexture(self.image, QOpenGLTexture.MipMapGeneration.DontGenerateMipMaps)
            if not self._texture.isCreated():
                raise RuntimeError('Cannot upload video frame')
            self._texture.setMinMagFilters(QOpenGLTexture.Filter.Linear, QOpenGLTexture.Filter.Linear)
            self._texture.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
            self._uploaded = self.image
        target = _fit(width, height, self.image)
        self._vao.bind()
        try:
            texture = self._cnn(gl, self._texture.textureId())
            gl.glBindFramebuffer(0x8D40, self.defaultFramebufferObject())
            gl.glViewport(round(target.x()), round(height - target.bottom()),
                          round(target.width()), round(target.height()))
            self._draw_pass(gl, self._programs[-1], [('frame', texture)])
        finally:
            self._vao.release()
        error = gl.glGetError()
        if error:
            raise RuntimeError(f'Anime4K OpenGL draw failed: {error:#x}')
        if self._ready != self.effective_passes:
            self._ready = self.effective_passes
            self.ready.emit()


class UpscaleView(QWidget):
    """Use ``player.setVideoSink(view.video_sink)`` to deliver frames.

    ``auto`` and ``opengl`` prefer OpenGL, with ``cpu`` as the raster fallback.
    ``cpu`` can also be selected explicitly. The queued ``backend_changed``
    notification reports ``opengl`` after the first successful frame, or
    ``cpu`` when raster rendering is selected.

    ``model`` selects Anime4K S, M, L, VL or UL; ``passes`` runs the full x2
    graph up to three times. ``scale`` sets the final intermediate texture size
    relative to the input; bilinear resampling follows the CNN if necessary.
    The widget fits that texture to its viewport using the input aspect ratio.
    Raster fallback does not run the CNN or allocate an intermediate texture.
    """

    backend_changed = Signal(str)

    def __init__(self, mode: str, parent: QWidget | None = None, *,
                 model: str = 'S', passes: int = 1, scale: float = 2, sharp: bool = False):
        if mode not in ('auto', 'opengl', 'cpu'):
            raise ValueError(f'Unknown upscale mode: {mode!r}')
        if model not in _GRAPHS:
            raise ValueError(f'Unknown Anime4K model: {model!r}')
        if type(passes) is not int or passes not in (1, 2, 3):
            raise ValueError(f'Expected 1, 2 or 3 CNN passes, got {passes!r}')
        if type(scale) not in (int, float) or scale not in (1.5, 2, 3, 4):
            raise ValueError(f'Unsupported Anime4K scale: {scale!r}')
        super().__init__(parent)
        self._backend = None
        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._cpu = _RasterSurface(self)
        self._stack.addWidget(self._cpu)
        self._gl = None
        if mode != 'cpu' and QGuiApplication.platformName() not in ('offscreen', 'minimal'):
            self._gl = _GLSurface(self, model, passes, scale, sharp)
            self._gl.ready.connect(self._on_gl_ready, Qt.ConnectionType.QueuedConnection)
            self._gl.failed.connect(self._use_cpu, Qt.ConnectionType.QueuedConnection)
            self._stack.addWidget(self._gl)
            self._stack.setCurrentWidget(self._gl)
        self._video_sink = QVideoSink(self)
        self._video_sink.videoFrameChanged.connect(self._on_frame)
        self._probe = QTimer(self, singleShot=True)
        self._probe.timeout.connect(self._check_context)

    @property
    def effective_passes(self):
        return self._gl.effective_passes if self._backend == 'opengl' and self._gl else None

    @property
    def video_sink(self) -> QVideoSink:
        return self._video_sink

    def showEvent(self, event):
        super().showEvent(event)
        self._probe.start(0)

    @Slot()
    def _check_context(self):
        if self._gl is None or (self.isVisible() and not self._gl.isValid()):
            self._use_cpu()

    @Slot()
    def _on_gl_ready(self):
        if self._gl is not None and not self._gl._failed:
            self._backend = 'opengl'
            self.backend_changed.emit('opengl')

    @Slot()
    def _use_cpu(self):
        if self._gl is not None:
            surface, self._gl = self._gl, None
            self._stack.setCurrentWidget(self._cpu)
            self._stack.removeWidget(surface)
            if surface.isValid():
                surface._cleanup()
            surface.deleteLater()
        if self._backend != 'cpu':
            self._backend = 'cpu'
            self.backend_changed.emit('cpu')

    @Slot(QVideoFrame)
    def _on_frame(self, frame):
        image = frame.toImage() if frame.isValid() else QImage()
        self._cpu.image = image
        active = self._stack.currentWidget()
        active.image = image
        active.update()
