"""Opt-in PCM processing for QMediaPlayer (Qt 6.8+ FFmpeg backend).

Create PlaybackAudio on the player's Qt thread with its existing QAudioOutput.
Use configure() instead of writing native volume/mute, seek() and stop() instead
of the player equivalents, and call flush() before source reloads/track changes
and close() before disposing the player. Keep the normal single-play loop mode.
Connect status_changed and use active/unavailable_reason for UI feedback; active
means PCM was accepted by the sink, not that hardware playback was measured.

The tap follows Qt's renderer scheduling, but the separate sink does not share
its clock. Buffer limits bound app-side latency, not device latency. Qt does not
rate-scale tap data, so non-1x uses the native path (without effects). Qt exposes
no decoder seek-complete or buffer generation ID; replacing the tap invalidates
queued callbacks from the old tap, not frames Qt might emit on the new tap.
"""

from array import array
from math import exp, isfinite, log10
from time import monotonic

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtMultimedia import QAudio, QAudioFormat, QAudioSink, QMediaDevices, QMediaPlayer

try:
    from PySide6.QtMultimedia import QAudioBufferOutput
except ImportError:  # The app also supports Qt 6.7.
    QAudioBufferOutput = None


_MAX_VOLUME = 200.0
_RATE = 1.0
_SINK_US = 60_000
_MAX_PENDING_US = 120_000
_NO_PCM_SECONDS = 2.0

# Native-endian Qt PCM: typecode, zero point, positive scale, integer maximum.
_FORMATS = {
    QAudioFormat.SampleFormat.UInt8: ("B", 128, 128, 255),
    QAudioFormat.SampleFormat.Int16: ("h", 0, 32768, 32767),
    QAudioFormat.SampleFormat.Int32: ("i", 0, 2147483648, 2147483647),
    QAudioFormat.SampleFormat.Float: ("f", 0, 1, None),
}


class PcmProcessor:
    """Linked peak compressor: -18 dBFS, 4:1, 8 ms attack, 120 ms release.

    Apply the volume multiplier after compression, then clip at full scale.
    Clipping is a safety ceiling, not a lookahead or true-peak limiter.
    """

    def __init__(self, fmt: QAudioFormat) -> None:
        if not fmt.isValid() or fmt.sampleFormat() not in _FORMATS:
            raise ValueError("Unsupported PCM format")
        self._layout = _FORMATS[fmt.sampleFormat()]
        self._channels = fmt.channelCount()
        self._attack = exp(-1 / (0.008 * fmt.sampleRate()))
        self._release = exp(-1 / (0.120 * fmt.sampleRate()))
        self._reduction = 0.0

    def process(self, pcm: bytes, gain: float, compressor: bool) -> bytes:
        code, zero, scale, maximum = self._layout
        samples = array(code)
        if len(pcm) % (samples.itemsize * self._channels):
            raise ValueError("PCM does not contain whole frames")
        samples.frombytes(pcm)
        reduction = self._reduction if compressor else 0.0
        for offset in range(0, len(samples), self._channels):
            end = offset + self._channels
            frame = [(x - zero) / scale if isfinite(x) else 0.0 for x in samples[offset:end]]
            if compressor:
                peak = max(map(abs, frame))
                target = (20 * log10(peak) + 18) * 0.75 if peak > 0.12589254 else 0.0
                coefficient = self._attack if target > reduction else self._release
                reduction = max(0.0, target + coefficient * (reduction - target))
            multiplier = gain * 10 ** (-reduction / 20) if reduction else gain
            for i, sample in enumerate(frame, offset):
                value = min(1.0, max(-1.0, sample * multiplier))
                samples[i] = value if maximum is None else min(maximum, round(value * scale + zero))
        self._reduction = reduction
        return samples.tobytes()


class PlaybackAudio(QObject):
    """Own the mutually exclusive native or processed audio route for a player."""

    status_changed = Signal()

    def __init__(self, player: QMediaPlayer, native_output) -> None:
        super().__init__(player)
        self._player = player
        self._native = native_output
        self._volume = native_output.volume() * 100
        self._muted = native_output.isMuted()
        self._compressor = False
        self._tap = self._sink = self._io = self._processor = None
        self._pending = bytearray()
        self._closed = self._draining = False
        self._last_pcm = monotonic()
        self.active = False
        self.unavailable_reason: str | None = None
        self._timer = QTimer(self, interval=10)
        self._timer.timeout.connect(self._pump)
        player.playbackRateChanged.connect(self._select_route)
        player.playbackStateChanged.connect(self._state_changed)
        player.mediaStatusChanged.connect(self._media_status)
        player.sourceChanged.connect(self.flush)
        player.errorOccurred.connect(self.flush)
        native_output.deviceChanged.connect(self.flush)

    def configure(self, *, volume_percent: float, compressor: bool, muted: bool = False) -> None:
        """Set 0–200% linear PCM gain; native fallback uses at most 100%."""
        if not isfinite(volume_percent):
            raise ValueError("Volume must be finite")
        self._volume = min(_MAX_VOLUME, max(0.0, volume_percent))
        self._compressor = compressor
        self._muted = muted
        self._select_route()
        self._native.setVolume(min(1.0, self._volume / 100))
        self._native.setMuted(self._muted or self.active)
        if self._sink is not None:
            # Sink volume is used only for immediate mute, never for boost.
            self._sink.setVolume(0.0 if muted else 1.0)

    def seek(self, position_ms: int) -> None:
        if self._player.isSeekable():
            had_tap = self._tap is not None
            if had_tap:
                self._detach_tap()
            self._player.setPosition(position_ms)
            if had_tap:
                self._select_route()

    def stop(self) -> None:
        self._player.stop()
        self.flush()

    def flush(self, *_args) -> None:
        """Discard app/sink queues and invalidate callbacks from the old tap."""
        if self._tap is not None:
            self._detach_tap()
            self._select_route()

    def close(self) -> None:
        self._closed = True
        self._use_native(None)

    def _report(self, active: bool, reason: str | None = None) -> None:
        if (active, reason) != (self.active, self.unavailable_reason):
            self.active, self.unavailable_reason = active, reason
            self.status_changed.emit()

    def _select_route(self, *_args) -> None:
        if self._closed:
            return
        if not (self._compressor or self._volume > 100):
            self._use_native(None)
        elif QAudioBufferOutput is None:
            self._use_native("Audio effects require Qt 6.8+ with the FFmpeg backend.")
        elif self._player.playbackRate() != _RATE:
            self._use_native("Audio effects are available only at 1× playback speed.")
        elif self._tap is None:
            device = self._native.device()
            if device.isNull():
                device = QMediaDevices.defaultAudioOutput()
            fmt = device.preferredFormat()
            if (device.isNull() or not fmt.isValid() or fmt.sampleFormat() not in _FORMATS
                    or not device.isFormatSupported(fmt)):
                self._use_native("No compatible audio output device for PCM effects.")
                return
            self._device, self._format = device, fmt
            self._tap = QAudioBufferOutput(fmt, self)
            self._tap.audioBufferReceived.connect(self._on_buffer, Qt.ConnectionType.QueuedConnection)
            self._player.setAudioBufferOutput(self._tap)
            self._last_pcm = monotonic()
            self._timer.start()
            self._report(False)

    def _detach_tap(self) -> None:
        self._timer.stop()
        tap, self._tap = self._tap, None
        if tap is not None:
            self._player.setAudioBufferOutput(None)
            tap.deleteLater()
        self._reset_sink()

    def _reset_sink(self) -> None:
        sink, self._sink = self._sink, None
        self._io = self._processor = None
        self._pending.clear()
        self._draining = False
        self._native.setMuted(self._muted)
        self._report(False)
        if sink is not None:
            sink.reset()  # stop() can drain on some platforms, unlike reset().
            sink.deleteLater()

    def _use_native(self, reason: str | None) -> None:
        self._detach_tap()
        self._native.setVolume(min(1.0, self._volume / 100))
        self._native.setMuted(self._muted)
        if self._player.audioOutput() is not self._native:
            self._player.setAudioOutput(self._native)
        self._report(False, reason)

    def _state_changed(self, state) -> None:
        self._last_pcm = monotonic()
        if self._sink is not None:
            if state == QMediaPlayer.PlaybackState.PausedState:
                self._sink.suspend()
            elif state == QMediaPlayer.PlaybackState.PlayingState:
                self._sink.resume()
        # A natural end also transitions to StoppedState. Do not drop its tail;
        # explicit stops must use stop() above.

    def _media_status(self, status) -> None:
        self._last_pcm = monotonic()
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._draining = self._sink is not None

    @Slot('QAudioBuffer')
    def _on_buffer(self, buffer) -> None:
        if self._tap is None or self.sender() is not self._tap:
            return
        if not buffer.isValid():
            self._draining = self._sink is not None
            return
        if self._player.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            if self._player.mediaStatus() != QMediaPlayer.MediaStatus.EndOfMedia:
                return
        try:
            data = bytes(buffer.constData())
            if buffer.format() != self._format or len(data) != buffer.byteCount():
                raise ValueError("Unexpected decoded PCM layout")
            self._accept_pcm(data)
        except (TypeError, ValueError, BufferError) as exc:
            self._use_native(f"Cannot process decoded audio: {exc}")

    def _accept_pcm(self, data: bytes) -> None:
        self._last_pcm = monotonic()
        frame_bytes = self._format.bytesPerFrame()
        cap = self._format.bytesForDuration(_MAX_PENDING_US)
        if len(data) % frame_bytes:
            raise ValueError("PCM does not contain whole frames")
        if len(self._pending) + len(data) > cap:
            # Catch up instead of playing increasingly stale audio after a burst.
            self._reset_sink()
            data = data[-cap:]
        if self._sink is None:
            self._processor = PcmProcessor(self._format)
            self._sink = QAudioSink(self._device, self._format, self)
            self._sink.setBufferSize(self._format.bytesForDuration(_SINK_US))
            self._sink.setVolume(0.0 if self._muted else 1.0)
            self._io = self._sink.start()
            if self._io is None:
                self._use_native("Could not open the processed audio sink.")
                return
            if self._player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
                self._sink.suspend()
        self._pending.extend(self._processor.process(data, self._volume / 100, self._compressor))
        if self._player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
            self._draining = True
        self._pump()

    def _pump(self) -> None:
        playing = self._player.isPlaying()
        status = self._player.mediaStatus()
        if playing and self._player.hasAudio() and status == QMediaPlayer.MediaStatus.BufferedMedia:
            if monotonic() - self._last_pcm > _NO_PCM_SECONDS:
                self._use_native("Qt did not deliver decoded audio for effects.")
                return
        else:
            self._last_pcm = monotonic()
        if (self._sink is None or not (playing or self._draining)
                or self._player.playbackState() == QMediaPlayer.PlaybackState.PausedState):
            return
        if self._sink.state() == QAudio.State.StoppedState:
            self._use_native("The processed audio sink stopped unexpectedly.")
            return
        if self._pending:
            frame_bytes = self._format.bytesPerFrame()
            # Some backends allocate more than the requested buffer. Limit how
            # much of that buffer we actually fill to keep audio close to video.
            free = self._sink.bytesFree()
            used = max(0, self._sink.bufferSize() - free)
            budget = self._format.bytesForDuration(_SINK_US) - used
            size = min(len(self._pending), free, budget)
            # A short write may end mid-frame; resume at that exact byte.
            size -= (size - len(self._pending)) % frame_bytes
            if size > 0:
                written = self._io.write(bytes(self._pending[:size]))
                if written < 0:
                    self._use_native("Could not write processed audio to the sink.")
                    return
                if written:
                    del self._pending[:written]
                    # Keep the native route alive until processed PCM is accepted.
                    self._native.setMuted(True)
                    self._report(True)
        elif self._draining and self._sink.state() == QAudio.State.IdleState:
            self._reset_sink()
            self._report(False)
