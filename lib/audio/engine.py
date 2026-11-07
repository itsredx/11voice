# ── Imports & Logging ──────────────────────────────────────────────────
import logging
from typing import Dict, List, Optional
from .backends.base import BaseAudioBackend, PlaybackHandle, PlaybackStatus
from .backends.pipewire import PipeWireBackend
from .devices import AudioDevice

logger = logging.getLogger(__name__)


# ── Audio Engine Orchestrator ──────────────────────────────────────────
class AudioEngine:
    """
    Central audio manager for discovering outputs and dispatching 
    audio playback to target physical and virtual audio devices.
    """

    def __init__(self, backend: Optional[BaseAudioBackend] = None):
        self._backend = backend or PipeWireBackend()
        self._devices: Dict[str, AudioDevice] = {}
        self.refresh_devices()

    # ── Device Management ─────────────────────────────────────────────
    def refresh_devices(self) -> List[AudioDevice]:
        """Query and cache available audio output sinks."""
        device_list = self._backend.list_devices()
        self._devices = {dev.id: dev for dev in device_list}
        return device_list

    def get_devices(self) -> List[AudioDevice]:
        """Return the current list of known audio output sinks."""
        if not self._devices:
            self.refresh_devices()
        return list(self._devices.values())

    def get_device_by_id(self, device_id: str) -> Optional[AudioDevice]:
        """Retrieve a specific AudioDevice by its node name or ID."""
        if not self._devices:
            self.refresh_devices()
        return self._devices.get(device_id)

    def get_default_device(self) -> Optional[AudioDevice]:
        """Return the detected default output sink."""
        for dev in self.get_devices():
            if dev.is_default:
                return dev
        devices = self.get_devices()
        return devices[0] if devices else None

    # ── Playback Dispatch ─────────────────────────────────────────────
    def play(
        self,
        audio_path: str,
        device_id: Optional[str] = None,
        on_status_change: Optional[callable] = None,
    ) -> PlaybackHandle:
        """
        Play an audio file routed to the requested device (or system default).
        """
        target_device = None
        if device_id:
            target_device = self.get_device_by_id(device_id)

        if not target_device:
            target_device = self.get_default_device()

        if not target_device:
            raise RuntimeError("No audio output device found or specified.")

        logger.info("Routing playback of '%s' to sink: %s", audio_path, target_device.name)
        return self._backend.play(
            audio_path=audio_path,
            device=target_device,
            on_status_change=on_status_change,
        )

    def stop_all(self) -> None:
        """Stop all active audio streams."""
        self._backend.stop_all()

