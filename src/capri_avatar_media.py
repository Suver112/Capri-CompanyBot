"""Paint Qt images, GIFs and decoded video frames with non-blocking cross-fades.

Each new media source is loaded and delivers a first usable frame before the
old source is released. QTimer/QMovie/QVideoSink stay on the GUI thread.
"""
from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Qt, QUrl
from PySide6.QtGui import QImage, QMovie, QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QVideoSink
from capri_avatar_emotions import smoothstep

VIDEO_SUFFIXES = {".mp4", ".webm", ".mov"}


class _FrameSource(QObject):
    def __init__(self, parent, path: str, changed, ready):
        super().__init__(parent)
        self.path = path
        self._changed = changed
        self._ready = ready
        self.alive = True
        self.image = None
        self.movie = None
        self.video = None
        self.sink = None
        extension = Path(path).suffix.lower()
        if extension in VIDEO_SUFFIXES:
            self.sink = QVideoSink(self)
            self.sink.videoFrameChanged.connect(self._video_frame)
            self.video = QMediaPlayer(self)
            self.video.setAudioOutput(None)  # Video avatars must never speak over Capri TTS.
            self.video.setVideoSink(self.sink) if hasattr(self.video, "setVideoSink") else self.video.setVideoOutput(self.sink)
            self.video.mediaStatusChanged.connect(self._video_status)
            self.video.setSource(QUrl.fromLocalFile(path))
            self.video.play()
        elif extension in (".gif", ".webp"):
            movie = QMovie(path, parent=self)
            if movie.isValid() and (extension == ".gif" or movie.frameCount() != 1):
                self.movie = movie
                self.movie.frameChanged.connect(self._gif_frame)
                self.movie.start()
                pixmap = movie.currentPixmap()
                if not pixmap.isNull():
                    self.image = pixmap
                    self._ready(self)
            else:
                movie.deleteLater()
                self._load_still(path)
        else:
            self._load_still(path)

    def _load_still(self, path):
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.image = pixmap
            self._ready(self)

    def _gif_frame(self, _index):
        if not self.alive or not self.movie:
            return
        frame = self.movie.currentPixmap()
        if not frame.isNull():
            first = self.image is None
            self.image = frame
            if first:
                self._ready(self)
            self._changed()

    def _video_frame(self, frame):
        if not self.alive or not frame.isValid():
            return
        img = frame.toImage()
        if img.isNull():
            return
        first = self.image is None
        self.image = img
        if first:
            self._ready(self)
        self._changed()

    def _video_status(self, status):
        if self.alive and self.video and status == QMediaPlayer.MediaStatus.EndOfMedia:
            # Qt Multimedia plugin support depends on installed Windows codecs.
            self.video.setPosition(0)
            self.video.play()

    def dispose(self):
        self.alive = False
        if self.movie:
            self.movie.stop()
        if self.video:
            self.video.stop()
            self.video.setVideoSink(None) if hasattr(self.video, "setVideoSink") else self.video.setVideoOutput(None)
            self.video.setSource(QUrl())
        self.deleteLater()


class AvatarMediaRenderer:
    """Double buffer: never blend in an unloaded frame or discard old on fail."""
    def __init__(self, host):
        self.host = host
        self.current = None
        self.incoming = None
        self.requested_path = None
        self.start_time = 0.0
        self.duration = 350
        self.crossfading = False
        self.timer = QTimer(host)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)
        self.load_timeout = QTimer(host)
        self.load_timeout.setSingleShot(True)
        self.load_timeout.timeout.connect(self._pending_timeout)
        self._unusable_paths = set()

    def show(self, path: str | None, transition_ms=350) -> None:
        if path is None:
            # No configured asset; caller may fall back to the legacy image.
            return
        path = str(path)
        if path == self.requested_path:
            return
        if path in self._unusable_paths or not Path(path).is_file():
            return
        if self.incoming:
            self.incoming.dispose()
            self.incoming = None
        self.crossfading = False
        self.timer.stop()
        self.load_timeout.stop()
        self.requested_path = path
        self.duration = max(80, min(2000, int(transition_ms)))
        candidate = _FrameSource(self.host, path, self.host.update, self._ready)
        # QPixmap callback can run before _FrameSource constructor returns.
        if candidate is self.current:
            return
        self.incoming = candidate
        if candidate.image is not None:
            self._ready(candidate)
        else:
            self.load_timeout.start(4000)

    def _ready(self, source):
        if not source.alive or source.path != self.requested_path or source is self.current:
            return
        # Initial image: no need to crossfade from a blank avatar.
        if self.current is None:
            if self.incoming and self.incoming is not source:
                self.incoming.dispose()
            self.current = source
            self.incoming = None
            self.crossfading = False
            self.load_timeout.stop()
            self.host.update()
            return
        if source is self.current:
            return
        self.incoming = source
        self.start_time = time.monotonic()
        self.crossfading = True
        self.load_timeout.stop()
        self.timer.start()
        self.host.update()

    def _pending_timeout(self):
        # Don't show a black video frame or leave the animation half-faded.
        if self.incoming and self.incoming.image is None:
            self._unusable_paths.add(self.incoming.path)
            self.incoming.dispose()
            self.incoming = None
            self.requested_path = self.current.path if self.current else None
            self.host.update()

    def _tick(self):
        ratio = (time.monotonic() - self.start_time) * 1000 / self.duration
        if ratio >= 1:
            self._finish()
        else:
            self.host.update()

    def _finish(self):
        self.timer.stop()
        self.crossfading = False
        if self.incoming and self.incoming.image is not None:
            old = self.current
            self.current = self.incoming
            self.incoming = None
            if old and old is not self.current:
                old.dispose()
        self.host.update()

    def clear(self):
        self.timer.stop()
        self.load_timeout.stop()
        if self.incoming:
            self.incoming.dispose()
            self.incoming = None
        if self.current:
            self.current.dispose()
            self.current = None
        self.requested_path = None
        self.crossfading = False
        self.host.update()

    def paint(self, painter, rect) -> bool:
        if self.current is None or self.current.image is None:
            return False
        if self.crossfading and self.incoming and self.incoming.image is not None:
            t = smoothstep((time.monotonic() - self.start_time) * 1000 / self.duration)
            painter.save()
            painter.setOpacity(1.0 - t)
            self._draw(painter, rect, self.current.image)
            painter.setOpacity(t)
            self._draw(painter, rect, self.incoming.image)
            painter.restore()
        else:
            self._draw(painter, rect, self.current.image)
        return True

    @staticmethod
    def _draw(painter, rect, image):
        if isinstance(image, QPixmap):
            painter.drawPixmap(rect, image, image.rect())
        elif isinstance(image, QImage):
            painter.drawImage(rect, image, image.rect())

    def close(self):
        self.timer.stop()
        self.load_timeout.stop()
        if self.incoming:
            self.incoming.dispose()
            self.incoming = None
        if self.current:
            self.current.dispose()
            self.current = None
