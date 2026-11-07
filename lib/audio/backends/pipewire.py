# ── Imports & GStreamer Setup ──────────────────────────────────────────
import logging
import os
import threading
import uuid
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse

import gi
gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst

from ..devices import AudioDevice, DeviceMonitor
from .base import BaseAudioBackend, PlaybackHandle, PlaybackStatus

logger = logging.getLogger(__name__)


# ── Background GLib Event Loop Thread ─────────────────────────────────
class GLibLoopThread(threading.Thread):
    """Dedicated background daemon thread to run GLib.MainLoop for GStreamer buses."""

    def __init__(self):
        super().__init__(name="GLibLoopThread", daemon=True)
        self.loop = GLib.MainLoop()

    def run(self):
        self.loop.run()

    def stop(self):
        if self.loop.is_running():
            self.loop.quit()


# ── PipeWire Audio Backend Implementation ──────────────────────────────
class PipeWireBackend(BaseAudioBackend):
    """
    PipeWire audio playback engine using GStreamer's pipewiresink.
    Directs audio to specific output sinks without changing system defaults.
    """

    def __init__(self):
        # Initialize GStreamer once
        if not Gst.is_initialized():
            Gst.init(None)

        self._device_monitor = DeviceMonitor()
        self._active_pipelines: Dict[str, Gst.Element] = {}
        self._active_handles: Dict[str, PlaybackHandle] = {}
        self._lock = threading.Lock()

        # Start background GLib main loop for bus message dispatching
        self._loop_thread = GLibLoopThread()
        self._loop_thread.start()

    def list_devices(self) -> List[AudioDevice]:
        """Fetch all discovered PipeWire output sinks."""
        return self._device_monitor.list_devices()

    def _to_uri(self, audio_path: str) -> str:
        """Ensure the path is a valid URI for GStreamer playbin."""
        parsed = urlparse(audio_path)
        if parsed.scheme:
            return audio_path
        abs_path = os.path.abspath(os.path.expanduser(audio_path))
        return f"file://{abs_path}"

    def play(
        self,
        audio_path: str,
        device: AudioDevice,
        on_status_change: Optional[Callable[[PlaybackHandle, PlaybackStatus], None]] = None,
    ) -> PlaybackHandle:
        """
        Play an audio file routed to the target PipeWire node.
        """
        playback_id = str(uuid.uuid4())[:8]
        uri = self._to_uri(audio_path)

        # ── Pipeline Creation ─────────────────────────────────────────
        pipeline = Gst.ElementFactory.make("playbin", f"playbin_{playback_id}")
        if not pipeline:
            raise RuntimeError("Failed to create GStreamer playbin element")

        sink = Gst.ElementFactory.make("pipewiresink", f"pw_sink_{playback_id}")
        if not sink:
            raise RuntimeError("Failed to create GStreamer pipewiresink element")

        # Route directly to target PipeWire node name or node ID
        if device.id:
            sink.set_property("target-object", device.id)

        pipeline.set_property("audio-sink", sink)
        pipeline.set_property("uri", uri)

        # ── Playback Handle Creation ──────────────────────────────────
        handle = PlaybackHandle(
            playback_id=playback_id,
            audio_path=audio_path,
            device=device,
            stop_callback=lambda: self.stop_by_id(playback_id),
            pause_callback=lambda: self._pause_by_id(playback_id),
            resume_callback=lambda: self._resume_by_id(playback_id),
        )

        with self._lock:
            self._active_pipelines[playback_id] = pipeline
            self._active_handles[playback_id] = handle

        # ── GStreamer Bus Watcher ──────────────────────────────────────
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus_message, playback_id, on_status_change)

        # Start playback
        pipeline.set_state(Gst.State.PLAYING)
        handle.status = PlaybackStatus.PLAYING
        if on_status_change:
            on_status_change(handle, PlaybackStatus.PLAYING)

        return handle

    def _on_bus_message(
        self,
        bus: Gst.Bus,
        message: Gst.Message,
        playback_id: str,
        on_status_change: Optional[Callable[[PlaybackHandle, PlaybackStatus], None]],
    ):
        """Handle GStreamer bus messages (EOS, ERROR, STATE_CHANGED)."""
        handle = self._active_handles.get(playback_id)
        if not handle:
            return

        t = message.type
        if t == Gst.MessageType.EOS:
            logger.info("Playback %s completed (EOS)", playback_id)
            handle.status = PlaybackStatus.COMPLETED
            self._cleanup_pipeline(playback_id)
            if on_status_change:
                on_status_change(handle, PlaybackStatus.COMPLETED)

        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            error_msg = f"{err.message} ({debug})"
            logger.error("Playback %s error: %s", playback_id, error_msg)
            handle.status = PlaybackStatus.ERROR
            handle.error_message = error_msg
            self._cleanup_pipeline(playback_id)
            if on_status_change:
                on_status_change(handle, PlaybackStatus.ERROR)

    def _cleanup_pipeline(self, playback_id: str):
        """Set pipeline to NULL and release resources."""
        with self._lock:
            pipeline = self._active_pipelines.pop(playback_id, None)
            if pipeline:
                pipeline.set_state(Gst.State.NULL)

    def _pause_by_id(self, playback_id: str):
        with self._lock:
            pipeline = self._active_pipelines.get(playback_id)
            if pipeline:
                pipeline.set_state(Gst.State.PAUSED)

    def _resume_by_id(self, playback_id: str):
        with self._lock:
            pipeline = self._active_pipelines.get(playback_id)
            if pipeline:
                pipeline.set_state(Gst.State.PLAYING)

    def stop_by_id(self, playback_id: str):
        """Halt playback for a specific playback stream ID."""
        with self._lock:
            handle = self._active_handles.get(playback_id)
            if handle:
                handle.status = PlaybackStatus.STOPPED
            pipeline = self._active_pipelines.pop(playback_id, None)
            if pipeline:
                pipeline.set_state(Gst.State.NULL)

    def stop(self, handle: PlaybackHandle) -> None:
        """Halt playback of the given handle."""
        self.stop_by_id(handle.playback_id)

    def stop_all(self) -> None:
        """Stop all active playback streams."""
        with self._lock:
            pids = list(self._active_pipelines.keys())
        for pid in pids:
            self.stop_by_id(pid)

