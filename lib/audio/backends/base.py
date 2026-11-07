# ── Imports & Abstract Definitions ─────────────────────────────────────
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Callable, Optional
from ..devices import AudioDevice


# ── Playback Status Enum ──────────────────────────────────────────────
class PlaybackStatus(Enum):
    IDLE = auto()
    BUFFERING = auto()
    PLAYING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    STOPPED = auto()
    ERROR = auto()


# ── Playback Handle ───────────────────────────────────────────────────
class PlaybackHandle:
    """Represents an active or finished audio playback task on a specific device."""

    def __init__(
        self,
        playback_id: str,
        audio_path: str,
        device: AudioDevice,
        stop_callback: Optional[Callable[[], None]] = None,
        pause_callback: Optional[Callable[[], None]] = None,
        resume_callback: Optional[Callable[[], None]] = None,
    ):
        self.playback_id = playback_id
        self.audio_path = audio_path
        self.device = device
        self.status = PlaybackStatus.IDLE
        self.error_message: Optional[str] = None
        self._stop_callback = stop_callback
        self._pause_callback = pause_callback
        self._resume_callback = resume_callback

    def stop(self) -> None:
        """Immediately halt playback."""
        if self._stop_callback:
            self._stop_callback()
        self.status = PlaybackStatus.STOPPED

    def pause(self) -> None:
        """Pause playback."""
        if self._pause_callback:
            self._pause_callback()
        self.status = PlaybackStatus.PAUSED

    def resume(self) -> None:
        """Resume playback if paused."""
        if self._resume_callback:
            self._resume_callback()
        self.status = PlaybackStatus.PLAYING


# ── Base Audio Backend Abstract Class ──────────────────────────────────
class BaseAudioBackend(ABC):
    """Abstract interface defining the audio output routing contract."""

    @abstractmethod
    def list_devices(self) -> list[AudioDevice]:
        """Return a list of available audio output sinks."""
        pass

    @abstractmethod
    def play(
        self,
        audio_path: str,
        device: AudioDevice,
        on_status_change: Optional[Callable[[PlaybackHandle, PlaybackStatus], None]] = None,
    ) -> PlaybackHandle:
        """
        Play an audio file routed directly to the specified target device.
        Must not alter the system default audio sink.
        """
        pass

    @abstractmethod
    def stop(self, handle: PlaybackHandle) -> None:
        """Stop a specific active playback stream."""
        pass

    @abstractmethod
    def stop_all(self) -> None:
        """Halt all ongoing playback streams across all outputs."""
        pass

