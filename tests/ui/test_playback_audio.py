from array import array
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QByteArray, QObject, Signal
from PySide6.QtMultimedia import QAudio, QAudioBuffer, QAudioFormat, QMediaPlayer
from PySide6.QtWidgets import QApplication

from anx_desktop.ui import playback_audio as audio


def pcm_format(sample_format=QAudioFormat.SampleFormat.Float):
    fmt = QAudioFormat()
    fmt.setSampleRate(48000)
    fmt.setChannelCount(2)
    fmt.setSampleFormat(sample_format)
    return fmt


def test_float_boost_clips_and_sanitizes():
    pcm = array('f', [0.25, -0.25, 0.9, -0.9, float('nan'), float('inf')])
    result = audio.PcmProcessor(pcm_format()).process(pcm.tobytes(), 2, False)
    assert list(array('f', result)) == [0.5, -0.5, 1, -1, 0, 0]


@pytest.mark.parametrize('name,code,values,expected', [
    ('UInt8', 'B', [128, 148, 255, 0], [128, 168, 255, 0]),
    ('Int16', 'h', [1, -1, 32767, -32768], [2, -2, 32767, -32768]),
    ('Int32', 'i', [1, -1, 2147483647, -2147483648], [2, -2, 2147483647, -2147483648]),
])
def test_integer_boost(name, code, values, expected):
    processor = audio.PcmProcessor(pcm_format(getattr(QAudioFormat.SampleFormat, name)))
    assert list(array(code, processor.process(array(code, values).tobytes(), 2, False))) == expected
    with pytest.raises(ValueError, match='whole frames'):
        processor.process(b'\x00', 1, False)


def test_compressor_links_channels_and_preserves_envelope_across_buffers():
    loud = array('f', [0.8, 0.08] * 3000).tobytes()
    quiet = array('f', [0.08, 0.04] * 24000).tobytes()
    processor = audio.PcmProcessor(pcm_format())
    attack = array('f', processor.process(loud, 1, True))
    release = array('f', processor.process(quiet, 1, True))
    assert attack[0] > attack[-2]
    assert attack[-2] == pytest.approx(0.2, abs=0.01)
    assert attack[-2] == pytest.approx(10 * attack[-1])
    assert release[0] < 0.03 < release[-2]
    assert attack.tobytes() + release.tobytes() == audio.PcmProcessor(pcm_format()).process(
        loud + quiet, 1, True
    )


class Player(QObject):
    playbackRateChanged = Signal(float)
    playbackStateChanged = Signal(object)
    mediaStatusChanged = Signal(object)
    sourceChanged = Signal(object)
    errorOccurred = Signal(object, str)
    rate = 1.0
    state = QMediaPlayer.PlaybackState.PlayingState
    status = QMediaPlayer.MediaStatus.BufferedMedia
    output = tap = None

    def setAudioOutput(self, value): self.output = value
    def audioOutput(self): return self.output
    def setAudioBufferOutput(self, value): self.tap = value
    def playbackRate(self): return self.rate
    def playbackState(self): return self.state
    def mediaStatus(self): return self.status
    def isPlaying(self): return self.state == QMediaPlayer.PlaybackState.PlayingState
    def hasAudio(self): return True
    def isSeekable(self): return True
    def setPosition(self, value): self.position = value
    def stop(self): self.state = QMediaPlayer.PlaybackState.StoppedState


class Native(QObject):
    deviceChanged = Signal()
    level = 1.0
    muted = False

    def device(self):
        return SimpleNamespace(isNull=lambda: False, preferredFormat=pcm_format,
                               isFormatSupported=lambda fmt: True)

    def volume(self): return self.level
    def setVolume(self, value): self.level = value
    def isMuted(self): return self.muted
    def setMuted(self, value): self.muted = value


class Sink(QObject):
    def __init__(self, device, fmt, parent):
        super().__init__(parent)
        self.data = bytearray()
        self.reset_called = False
        self.suspended = False
        self.state_value = QAudio.State.ActiveState

    def setBufferSize(self, size): self.size = size
    def setVolume(self, value): self.volume = value
    def start(self): return self
    def stop(self): pytest.fail('flush must reset, not drain')
    def reset(self): self.reset_called = True
    def state(self): return self.state_value
    def bytesFree(self): return self.size
    def bufferSize(self): return self.size
    def suspend(self): self.suspended = True
    def resume(self): self.suspended = False

    def write(self, data):
        self.data.extend(data[:3])  # Exercise even a short write that ends mid-frame.
        return min(3, len(data))


@pytest.fixture
def route(monkeypatch):
    app = QApplication.instance() or QApplication([])
    player = Player()
    native = Native()
    player.setAudioOutput(native)
    monkeypatch.setattr(audio, 'QAudioSink', Sink)
    router = audio.PlaybackAudio(player, native)
    yield app, player, native, router
    router.close()


@pytest.mark.skipif(audio.QAudioBufferOutput is None, reason='requires Qt 6.8+')
def test_route_processes_real_qt_buffer_and_flushes_on_seek(route):
    app, player, native, router = route
    router.configure(volume_percent=150, compressor=False)
    assert player.output is native and not native.muted
    buf = QAudioBuffer(QByteArray(array('f', [.25, -.25]).tobytes()), pcm_format())
    player.tap.audioBufferReceived.emit(buf)
    app.processEvents()
    sink = router._sink
    router._pump()
    router._pump()
    assert list(array('f', sink.data)) == [.375, -.375]
    assert router.active and native.muted

    player.state = QMediaPlayer.PlaybackState.PausedState
    player.playbackStateChanged.emit(player.state)
    assert sink.suspended
    player.state = QMediaPlayer.PlaybackState.PlayingState
    player.playbackStateChanged.emit(player.state)
    assert not sink.suspended

    old_tap = player.tap
    old_tap.audioBufferReceived.emit(buf)
    router.seek(1000)
    app.processEvents()
    assert player.position == 1000 and player.tap is not old_tap
    assert sink.reset_called and router._sink is None and not router.active
    assert not native.muted
    player.rate = 1.5
    player.playbackRateChanged.emit(1.5)
    assert player.tap is None and player.output is native and native.level == 1.0
    assert '1×' in router.unavailable_reason


@pytest.mark.skipif(audio.QAudioBufferOutput is None, reason='requires Qt 6.8+')
def test_end_drains_and_missing_pcm_falls_back(route, monkeypatch):
    app, player, native, router = route
    router.configure(volume_percent=70, compressor=True)
    buf = QAudioBuffer(QByteArray(array('f', [.05, -.05]).tobytes()), pcm_format())
    player.tap.audioBufferReceived.emit(buf)
    player.tap.audioBufferReceived.emit(QAudioBuffer())
    app.processEvents()
    player.stop()
    player.status = QMediaPlayer.MediaStatus.EndOfMedia
    player.mediaStatusChanged.emit(player.status)
    sink = router._sink
    router._pump()
    router._pump()
    assert len(sink.data) == 8 and not sink.reset_called
    sink.state_value = QAudio.State.IdleState
    router._pump()
    assert sink.reset_called and not router.active

    player.state = QMediaPlayer.PlaybackState.PlayingState
    player.status = QMediaPlayer.MediaStatus.BufferedMedia
    monkeypatch.setattr(audio, 'monotonic', lambda: router._last_pcm + 3)
    router._pump()
    assert player.output is native and native.level == .7 and player.tap is None
    assert 'did not deliver' in router.unavailable_reason


@pytest.mark.skipif(audio.QAudioBufferOutput is None, reason='requires Qt 6.8+')
def test_overflow_and_stop_discard_queued_pcm(route):
    app, player, _, router = route
    router.configure(volume_percent=150, compressor=True)
    fmt = pcm_format()
    frame = array('f', [.25, -.25]).tobytes()
    buf = QAudioBuffer(QByteArray(frame), fmt)
    player.tap.audioBufferReceived.emit(buf)
    app.processEvents()
    initial_sink = router._sink

    burst = QAudioBuffer(QByteArray(frame * 8000), fmt)
    player.tap.audioBufferReceived.emit(burst)
    app.processEvents()
    assert initial_sink.reset_called
    sink = router._sink
    assert 0 < len(router._pending) <= fmt.bytesForDuration(120_000)
    router.stop()
    assert sink.reset_called and not router._pending and not router.active


def test_old_qt_keeps_normal_audio(route, monkeypatch):
    _, player, native, router = route
    monkeypatch.setattr(audio, 'QAudioBufferOutput', None)
    router.configure(volume_percent=180, compressor=True, muted=True)
    assert player.output is native and native.level == 1.0 and native.muted
    assert not router.active and 'Qt 6.8' in router.unavailable_reason
