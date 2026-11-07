# ── Imports & Setup ──────────────────────────────────────────────────
import logging
from typing import Dict, List, Optional
from ..audio import AudioEngine
from ..storage.audio_cache import AudioCache
from .models import Conversation, DialogueTurn, GenerationStatus, Speaker
from .queue import PlaybackQueue

logger = logging.getLogger(__name__)


# ── Conversation Manager ──────────────────────────────────────────────
class ConversationManager:
    """
    Manages conversation lifecycle, turn manipulation, speaker assignments,
    and ties into the sequential multi-device PlaybackQueue.
    """

    def __init__(
        self,
        audio_engine: Optional[AudioEngine] = None,
        audio_cache: Optional[AudioCache] = None,
    ):
        self.audio_engine = audio_engine or AudioEngine()
        self.audio_cache = audio_cache or AudioCache()
        self.queue = PlaybackQueue(audio_engine=self.audio_engine)

        self.current_conversation = Conversation(title="New Conversation")
        self.speakers: Dict[str, Speaker] = {}

    # ── Speaker Operations ────────────────────────────────────────────
    def add_speaker(self, name: str, voice_id: str, output_device_id: Optional[str] = None) -> Speaker:
        """Create and register a speaker."""
        speaker = Speaker(
            name=name,
            voice_id=voice_id,
            output_device_id=output_device_id,
        )
        self.speakers[speaker.id] = speaker
        return speaker

    def update_speaker(
        self,
        speaker_id: str,
        name: Optional[str] = None,
        voice_id: Optional[str] = None,
        output_device_id: Optional[str] = None,
    ) -> Optional[Speaker]:
        """Update an existing speaker's profile."""
        speaker = self.speakers.get(speaker_id)
        if not speaker:
            return None
        if name is not None:
            speaker.name = name
        if voice_id is not None:
            speaker.voice_id = voice_id
        if output_device_id is not None:
            speaker.output_device_id = output_device_id
        return speaker

    # ── Turn Operations ───────────────────────────────────────────────
    def add_turn(
        self,
        speaker_id: str,
        text: str,
        audio_path: Optional[str] = None,
        output_device_override: Optional[str] = None,
    ) -> DialogueTurn:
        """Append a dialogue turn to the conversation."""
        pos = len(self.current_conversation.turns)
        turn = DialogueTurn(
            conversation_id=self.current_conversation.id,
            speaker_id=speaker_id,
            text=text,
            audio_path=audio_path,
            generation_status=GenerationStatus.READY if audio_path else GenerationStatus.PENDING,
            position=pos,
            output_device_override=output_device_override,
        )
        self.current_conversation.turns.append(turn)
        return turn

    def update_turn_text(self, turn_id: str, new_text: str) -> Optional[DialogueTurn]:
        """
        Update the dialogue text for a turn.
        Invalidates existing audio reference so regenerated audio reflects changes.
        """
        for turn in self.current_conversation.turns:
            if turn.id == turn_id:
                if turn.text != new_text:
                    turn.text = new_text
                    turn.audio_path = None
                    turn.generation_status = GenerationStatus.PENDING
                return turn
        return None

    def remove_turn(self, turn_id: str) -> bool:
        """Remove a turn and re-index positions."""
        turns = self.current_conversation.turns
        for i, turn in enumerate(turns):
            if turn.id == turn_id:
                turns.pop(i)
                for idx, remaining in enumerate(turns):
                    remaining.position = idx
                return True
        return False

    # ── Playback Controls ─────────────────────────────────────────────
    def play_conversation(self, start_index: int = 0) -> None:
        """Start sequential playback from a turn index."""
        self.queue.start(
            turns=self.current_conversation.turns,
            speakers=self.speakers,
            start_index=start_index,
        )

    def pause_playback(self) -> None:
        self.queue.pause()

    def resume_playback(self) -> None:
        self.queue.resume()

    def stop_playback(self) -> None:
        self.queue.stop()

