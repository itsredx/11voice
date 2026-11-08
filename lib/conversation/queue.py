# ── Imports & Setup ──────────────────────────────────────────────────
import logging
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional
from ..audio import AudioEngine, AudioDevice, PlaybackHandle, PlaybackStatus
from ..elevenlabs.exceptions import PaidPlanRequiredError
from ..elevenlabs.speech import SpeechGenerator
from .models import Conversation, DialogueTurn, GenerationStatus, Speaker

logger = logging.getLogger(__name__)


# ── Conversation Playback Queue ───────────────────────────────────────
class PlaybackQueue:
    """
    Sequences dialogue turns, routes each speaker to their assigned audio device,
    and manages conversation play, pause, skip, and stop state.
    """

    def __init__(
        self,
        audio_engine: AudioEngine,
        speech_generator: Optional[SpeechGenerator] = None,
    ):
        self.audio_engine = audio_engine
        self.speech_generator = speech_generator or SpeechGenerator()
        
        self._current_turn_index: int = -1
        self._is_playing: bool = False
        self._is_paused: bool = False
        self._stop_requested: bool = False
        self._worker_thread: Optional[threading.Thread] = None
        self._current_handle: Optional[PlaybackHandle] = None
        self._lock = threading.Lock()

        # ── Callbacks ─────────────────────────────────────────────────
        self.on_turn_started: Optional[Callable[[DialogueTurn, Speaker, Optional[AudioDevice]], None]] = None
        self.on_turn_completed: Optional[Callable[[DialogueTurn], None]] = None
        self.on_playback_finished: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[DialogueTurn, str], None]] = None

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def current_turn_index(self) -> int:
        return self._current_turn_index

    # ── Playback Execution ────────────────────────────────────────────
    def start(
        self,
        turns: List[DialogueTurn],
        speakers: Dict[str, Speaker],
        start_index: int = 0,
    ) -> None:
        """Begin sequential playback of the dialogue turns."""
        self.stop()

        with self._lock:
            self._is_playing = True
            self._is_paused = False
            self._stop_requested = False
            self._current_turn_index = start_index

        self._worker_thread = threading.Thread(
            target=self._run_queue,
            args=(turns, speakers),
            name="PlaybackQueueWorker",
            daemon=True,
        )
        self._worker_thread.start()

    def _run_queue(self, turns: List[DialogueTurn], speakers: Dict[str, Speaker]) -> None:
        """Worker thread loop advancing through turns sequentially."""
        try:
            while self._current_turn_index < len(turns):
                if self._stop_requested:
                    break

                # Handle pause
                while self._is_paused and not self._stop_requested:
                    time.sleep(0.1)
                if self._stop_requested:
                    break

                turn = turns[self._current_turn_index]
                speaker = speakers.get(turn.speaker_id, Speaker(name="Unknown Speaker"))

                # Determine target audio device
                target_device_id = turn.output_device_override or speaker.output_device_id
                target_device = (
                    self.audio_engine.get_device_by_id(target_device_id)
                    if target_device_id
                    else self.audio_engine.get_default_device()
                )

                # Ensure audio file is generated / cached
                cached_path = self.speech_generator.get_cached_path(
                    text=turn.text,
                    voice_id=speaker.voice_id,
                    speaking_rate=speaker.speaking_rate,
                )
                audio_path = str(cached_path) if cached_path else None
                if (
                    not audio_path
                    and turn.audio_path
                    and turn.generation_status == GenerationStatus.READY
                    and Path(turn.audio_path).is_file()
                ):
                    audio_path = turn.audio_path
                if not audio_path:
                    try:
                        turn.generation_status = GenerationStatus.GENERATING
                        cached_path = self.speech_generator.generate(
                            text=turn.text,
                            voice_id=speaker.voice_id,
                            speaking_rate=speaker.speaking_rate,
                        )
                        audio_path = str(cached_path)
                        turn.audio_path = audio_path
                        turn.generation_status = GenerationStatus.READY
                    except Exception as e:
                        logger.error("Failed to generate audio for turn %s: %s", turn.id, e)
                        turn.generation_status = GenerationStatus.FAILED
                        if self.on_error:
                            self.on_error(turn, str(e))
                        if isinstance(e, PaidPlanRequiredError):
                            break
                        self._current_turn_index += 1
                        continue
                else:
                    turn.audio_path = audio_path
                    turn.generation_status = GenerationStatus.READY

                # Notify turn start
                if self.on_turn_started:
                    self.on_turn_started(turn, speaker, target_device)

                # Dispatch playback to target device
                try:
                    handle = self.audio_engine.play(
                        audio_path=audio_path,
                        device_id=target_device.id if target_device else None,
                    )
                    with self._lock:
                        self._current_handle = handle

                    # Wait for turn playback to finish
                    while handle.status not in (
                        PlaybackStatus.COMPLETED,
                        PlaybackStatus.STOPPED,
                        PlaybackStatus.ERROR,
                    ):
                        if self._stop_requested:
                            handle.stop()
                            break
                        time.sleep(0.05)

                    if handle.status == PlaybackStatus.ERROR:
                        if self.on_error:
                            self.on_error(turn, handle.error_message or "Playback error")

                except Exception as e:
                    logger.error("Error playing turn %s: %s", turn.id, e)
                    if self.on_error:
                        self.on_error(turn, str(e))

                # Notify turn completed
                if self.on_turn_completed:
                    self.on_turn_completed(turn)

                self._current_turn_index += 1

        finally:
            with self._lock:
                self._is_playing = False
                self._is_paused = False
                self._current_handle = None

            if self.on_playback_finished:
                self.on_playback_finished()

    # ── Controls ──────────────────────────────────────────────────────
    def pause(self) -> None:
        """Pause playback of the active turn."""
        with self._lock:
            if self._is_playing and not self._is_paused:
                self._is_paused = True
                if self._current_handle:
                    self._current_handle.pause()

    def resume(self) -> None:
        """Resume playback of the paused turn."""
        with self._lock:
            if self._is_playing and self._is_paused:
                self._is_paused = False
                if self._current_handle:
                    self._current_handle.resume()

    def stop(self) -> None:
        """Immediately stop playback and abort queue."""
        with self._lock:
            self._stop_requested = True
            if self._current_handle:
                self._current_handle.stop()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        self.audio_engine.stop_all()

    def skip(self) -> None:
        """Skip to the next turn immediately."""
        with self._lock:
            if self._current_handle:
                self._current_handle.stop()

