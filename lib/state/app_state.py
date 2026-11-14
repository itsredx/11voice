# ── Imports & Setup ──────────────────────────────────────────────────
import logging
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Callable, Dict, List, Optional
from ..audio import AudioDevice, AudioEngine, PlaybackStatus
from ..backend import Database
from ..conversation import Conversation, ConversationManager, DialogueTurn, GenerationStatus, Speaker
from ..elevenlabs import PaidPlanRequiredError, SpeechGenerator, VoiceInfo, VoiceManager
from ..storage import AudioCache, PlaybackArchive
from ..speechify import SpeechifyVoiceManager
from ..conversation.json_import import load_conversation_json

logger = logging.getLogger(__name__)


# ── Global Reactive Application State ──────────────────────────────────
class AppState:
    """
    Central reactive state store for Conversation Studio.
    Coordinates between audio playback, database persistence, and UI rebuilds.
    """

    _instance: Optional["AppState"] = None

    @classmethod
    def get(cls) -> "AppState":
        if cls._instance is None:
            cls._instance = AppState()
        return cls._instance

    def __init__(self):
        self._listeners: List[Callable[[], None]] = []

        # ── Backend Engine Singletons ─────────────────────────────────
        self.audio_engine = AudioEngine()
        self.audio_cache = AudioCache()
        self.playback_archive = PlaybackArchive()
        self.database = Database()
        self.speech_generator = SpeechGenerator(cache=self.audio_cache)
        self.active_provider = self.database.get_setting("active_provider") or "elevenlabs"
        if self.active_provider not in {"elevenlabs", "speechify"}:
            self.active_provider = "elevenlabs"
        self.speech_generator.set_provider(self.active_provider)
        self.voice_manager = VoiceManager(client=self.speech_generator.client)
        self.speechify_voice_manager = SpeechifyVoiceManager(
            client=self.speech_generator.speechify_client
        )
        self.voice_managers = {
            "elevenlabs": self.voice_manager,
            "speechify": self.speechify_voice_manager,
        }
        self.voice_catalogs = {"elevenlabs": [], "speechify": []}
        self.conversation_manager = ConversationManager(
            audio_engine=self.audio_engine,
            audio_cache=self.audio_cache,
            speech_generator=self.speech_generator,
        )

        # ── Reactive State Variables ──────────────────────────────────
        self.active_turn_id: Optional[str] = None
        self.status_message: str = "Ready"
        self.is_generating: bool = False
        self.is_refreshing_devices: bool = False
        self._last_playback_error: Optional[str] = None
        self.available_voices: List[VoiceInfo] = []
        try:
            selections = json.loads(
                self.database.get_setting("provider_voice_selections") or "{}"
            )
            self._provider_voice_selections = selections if isinstance(selections, dict) else {}
        except (TypeError, json.JSONDecodeError):
            self._provider_voice_selections = {}

        # Initialize speakers from DB or defaults
        self._init_default_speakers()
        self._register_bundled_conversations()
        # Restore the last selected script rather than always showing the
        # temporary starter dialogue after an app restart.
        saved_conversation_id = self.database.get_setting("active_conversation_id")
        if saved_conversation_id:
            saved_conversation = self.database.get_conversation(saved_conversation_id)
            if saved_conversation:
                self.conversation_manager.current_conversation = saved_conversation

        # Connect playback queue callbacks to UI listeners
        self._bind_queue_callbacks()
        self._connect_provider(self.active_provider)

    def _connect_provider(self, provider: str) -> None:
        """Load a provider's voice catalog without blocking the UI thread."""
        manager = self.voice_managers[provider]
        if not manager.client.api_key:
            label = "ElevenLabs" if provider == "elevenlabs" else "Speechify"
            self.status_message = f"{label} disconnected · add its API key in Settings"
            self.notify_listeners()
            return

        label = "ElevenLabs" if provider == "elevenlabs" else "Speechify"
        self.status_message = f"Connecting to {label}…"
        self.notify_listeners()

        def worker():
            try:
                voices = manager.fetch_voices(force_refresh=True)
                if provider == "elevenlabs":
                    voices = [voice for voice in voices if not voice.is_library_voice]
                self.voice_catalogs[provider] = voices
                if self.active_provider == provider:
                    self.available_voices = voices
                    self._restore_provider_voices(provider)
                    self.status_message = f"{label} connected · {len(voices)} voices loaded"
            except Exception as exc:
                logger.warning("Could not connect to %s: %s", label, exc)
                if self.active_provider == provider:
                    self.status_message = f"{label} connection failed: {exc}"
            if self.active_provider == provider:
                self.notify_listeners()

        threading.Thread(target=worker, name=f"{provider.title()}VoiceCatalog", daemon=True).start()

    def _persist_provider_voice_selections(self) -> None:
        self.database.set_setting(
            "provider_voice_selections", json.dumps(self._provider_voice_selections)
        )

    def _remember_current_provider_voices(self) -> None:
        self._provider_voice_selections[self.active_provider] = {
            speaker_id: speaker.voice_id for speaker_id, speaker in self.speakers.items()
        }
        self._persist_provider_voice_selections()

    def _restore_provider_voices(self, provider: str) -> None:
        voices = self.voice_catalogs.get(provider, [])
        if not voices and provider == "elevenlabs":
            from ..elevenlabs.voices import FALLBACK_USABLE_VOICES
            voices = FALLBACK_USABLE_VOICES
        if not voices:
            return
        valid_ids = {voice.voice_id for voice in voices}
        saved = self._provider_voice_selections.get(provider, {})
        default_voice_id = voices[0].voice_id
        for speaker_id, speaker in self.speakers.items():
            current_voice_id = speaker.voice_id if speaker.voice_id in valid_ids else default_voice_id
            speaker.voice_id = saved.get(speaker_id, current_voice_id)
            if speaker.voice_id not in valid_ids:
                speaker.voice_id = default_voice_id
            self.database.save_speaker(speaker)
        self._provider_voice_selections[provider] = {
            speaker_id: speaker.voice_id for speaker_id, speaker in self.speakers.items()
        }
        self._persist_provider_voice_selections()

    def switch_provider(self) -> None:
        turn_work_active = any(
            turn.generation_status == GenerationStatus.GENERATING
            for turn in self.conversation.turns
        )
        if self.is_playing or self.is_generating or turn_work_active or self.active_turn_id:
            self.status_message = "Stop playback and synthesis before switching providers"
            self.notify_listeners()
            return
        self._remember_current_provider_voices()
        self.active_provider = "speechify" if self.active_provider == "elevenlabs" else "elevenlabs"
        self.database.set_setting("active_provider", self.active_provider)
        self.speech_generator.set_provider(self.active_provider)
        self.available_voices = self.voice_catalogs.get(self.active_provider, [])
        self._restore_provider_voices(self.active_provider)
        # Paths persisted by the other provider must not be reused as fallbacks.
        for conversation_id, _ in self.database.list_conversations():
            conversation = self.database.get_conversation(conversation_id)
            if not conversation:
                continue
            for turn in conversation.turns:
                turn.audio_path = None
                turn.generation_status = GenerationStatus.PENDING
            self.database.save_conversation(conversation)
        for turn in self.conversation.turns:
            turn.audio_path = None
            turn.generation_status = GenerationStatus.PENDING
        self.database.save_conversation(self.conversation)
        provider = self.active_provider
        self.status_message = f"Switched to {provider.title()}"
        self.notify_listeners()
        if not self.voice_catalogs.get(provider):
            self._connect_provider(provider)

    def save_provider_api_key(self, provider: str, api_key: str) -> None:
        env_name = "ELEVENLABS_API_KEY" if provider == "elevenlabs" else "SPEECHIFY_API_KEY"
        if provider not in self.voice_managers:
            raise ValueError(f"Unknown provider: {provider}")
        key = api_key.strip().replace("\n", "").replace("\r", "")
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        kept, replaced = [], False
        for line in lines:
            name, separator, _ = line.partition("=")
            if separator and name.strip() == env_name:
                if key:
                    kept.append(f"{env_name}={key}")
                replaced = True
            else:
                kept.append(line)
        if key and not replaced:
            kept.append(f"{env_name}={key}")
        env_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
        try:
            env_path.chmod(0o600)
        except OSError:
            pass
        manager = self.voice_managers[provider]
        manager.client.api_key = key
        os.environ[env_name] = key
        self.voice_catalogs[provider] = []
        if provider == self.active_provider:
            self.available_voices = []
            self._connect_provider(provider)
        else:
            self.status_message = f"{provider.title()} API key {'saved' if key else 'removed'}"
            self.notify_listeners()

    def has_provider_api_key(self, provider: str) -> bool:
        return bool(self.voice_managers[provider].client.api_key)

    def _speechify_ready(self) -> bool:
        if self.active_provider != "speechify":
            return True
        if self.speechify_voice_manager.client.api_key and self.available_voices:
            return True
        self.status_message = "Add a Speechify API key in Settings and wait for voices to load"
        self.notify_listeners()
        return False

    def _handle_paid_plan_required(self) -> str:
        """Stop retries and leave non-library account voices selectable."""
        self.available_voices = [
            voice for voice in self.available_voices if not voice.is_library_voice
        ]
        return (
            "This Voice Library voice requires a paid ElevenLabs plan for API use. "
            "Voice Library voices are hidden. Select an account voice to continue."
        )

    # ── Listener Subscription ─────────────────────────────────────────
    def add_listener(self, listener: Callable[[], None]) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def notify_listeners(self) -> None:
        for listener in list(self._listeners):
            try:
                listener()
            except Exception as e:
                logger.error("Error in AppState listener callback: %s", e)

    # ── Initialization & Defaults ─────────────────────────────────────
    def _init_default_speakers(self) -> None:
        saved_speakers = self.database.get_speakers()
        default_device = self.audio_engine.get_default_device()
        default_dev_id = default_device.id if default_device else ""

        if not saved_speakers:
            # Default Speaker A
            spk_a = Speaker(
                id="spk_a",
                name="Speaker A (Host)",
                voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel
                output_device_id=default_dev_id,
            )
            # Default Speaker B
            devices = self.audio_engine.get_devices()
            secondary_dev_id = devices[1].id if len(devices) > 1 else default_dev_id
            spk_b = Speaker(
                id="spk_b",
                name="Speaker B (Guest)",
                voice_id="AZnzlk1XvdvUeBnXmlld",  # Domi
                output_device_id=secondary_dev_id,
            )
            self.database.save_speaker(spk_a)
            self.database.save_speaker(spk_b)
            self.conversation_manager.speakers = {"spk_a": spk_a, "spk_b": spk_b}
        else:
            self.conversation_manager.speakers = saved_speakers

        # Load or create conversation
        if not self.conversation_manager.current_conversation.turns:
            spk_keys = list(self.conversation_manager.speakers.keys())
            if len(spk_keys) >= 2:
                self.conversation_manager.add_turn(
                    speaker_id=spk_keys[0],
                    text="Welcome to Conversation Studio on Linux with PipeWire.",
                )
                self.conversation_manager.add_turn(
                    speaker_id=spk_keys[1],
                    text="Glad to be here! This stream is routed independently.",
                )
                self.database.save_conversation(self.conversation_manager.current_conversation)

    def _register_bundled_conversations(self) -> None:
        """Make JSON scripts shipped with the project available in the library."""
        scripts_dir = Path(__file__).resolve().parent.parent.parent / "conversations"
        saved_ids = {conversation_id for conversation_id, _ in self.database.list_conversations()}
        for script_path in sorted(scripts_dir.glob("*.json")):
            try:
                payload = json.loads(script_path.read_text(encoding="utf-8"))
                conversation_id = str(payload.get("id", ""))
                if conversation_id in saved_ids:
                    continue
                conversation, imported_speakers = load_conversation_json(
                    script_path,
                    self.conversation_manager.speakers,
                )
                for speaker in imported_speakers.values():
                    self.database.save_speaker(speaker)
                self.conversation_manager.speakers.update(imported_speakers)
                self.database.save_conversation(conversation)
                saved_ids.add(conversation.id)
            except Exception as exc:
                logger.warning("Could not register bundled conversation %s: %s", script_path.name, exc)

    def import_conversation_json(
        self,
        path: str | Path,
        reuse_existing: bool = False,
    ) -> Conversation:
        """Import a JSON conversation, save it, and make it the active script.

        Bundled conversation buttons use ``reuse_existing`` so they run through
        this known-good activation path without creating a duplicate each click.
        """
        source = Path(path)
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not read JSON file: {exc}") from exc
        existing_ids = {conversation_id for conversation_id, _ in self.database.list_conversations()}
        source_id = str(payload.get("id") or "") if isinstance(payload, dict) else ""
        if reuse_existing and source_id in existing_ids:
            if self.load_conversation(source_id):
                return self.conversation
        imported_id = source_id if source_id and source_id not in existing_ids else uuid.uuid4().hex[:8]
        conversation, imported_speakers = load_conversation_json(
            source,
            self.conversation_manager.speakers,
            conversation_id=imported_id,
        )
        for speaker in imported_speakers.values():
            self.database.save_speaker(speaker)
        self.conversation_manager.speakers.update(imported_speakers)
        self.database.save_conversation(conversation)
        self.conversation_manager.current_conversation = conversation
        self.database.set_setting("active_conversation_id", conversation.id)
        self.status_message = f"Imported {conversation.title}"
        self.notify_listeners()
        return conversation

    def load_conversation(self, conversation_id: str) -> bool:
        """Switch to a saved conversation and resolve audio for current voices."""
        if self.is_playing:
            self.stop()
        conversation = self.database.get_conversation(conversation_id)
        if not conversation:
            return False
        self.conversation_manager.current_conversation = conversation
        self.database.set_setting("active_conversation_id", conversation.id)
        for turn in conversation.turns:
            speaker = self.speakers.get(turn.speaker_id)
            if not speaker:
                continue
            cached = self._resolve_turn_audio(turn, speaker)
            if cached:
                turn.audio_path = str(cached)
                turn.generation_status = GenerationStatus.READY
            else:
                turn.audio_path = None
                turn.generation_status = GenerationStatus.PENDING
        self.status_message = f"Loaded {conversation.title}"
        self.notify_listeners()
        return True

    def _archive_turn_audio(self, turn: DialogueTurn) -> None:
        if turn.audio_path:
            self.playback_archive.archive_turn(
                self.conversation,
                turn,
                self.speakers,
                turn.audio_path,
            )

    def _resolve_turn_audio(self, turn: DialogueTurn, speaker: Speaker) -> Optional[Path]:
        """Resolve this voice's cache entry, restoring it from the archive if needed."""
        cached = self.speech_generator.get_cached_path(
            turn.text,
            speaker.voice_id,
            speaking_rate=speaker.speaking_rate,
        )
        if cached:
            return cached
        archived = self.playback_archive.find_turn(self.conversation, turn, self.speakers)
        if not archived:
            return None
        extension = archived.suffix.lstrip(".") or "wav"
        cache_key = self.audio_cache.derive_cache_key(
            speaker.voice_id,
            turn.text,
            speaking_rate=speaker.speaking_rate,
        )
        return self.audio_cache.store(cache_key, archived.read_bytes(), extension=extension)

    def _bind_queue_callbacks(self) -> None:
        queue = self.conversation_manager.queue

        def on_turn_started(turn: DialogueTurn, speaker: Speaker, dev: Optional[AudioDevice]):
            self.active_turn_id = turn.id
            turns = self.conversation.turns
            try:
                turn_number = turns.index(turn) + 1
            except ValueError:
                turn_number = queue.current_turn_index + 1
            total_turns = len(turns)
            dev_name = dev.name if dev else "Default"
            self.status_message = (
                f"Playing line {turn_number} of {total_turns} · "
                f"{speaker.name} -> {dev_name}"
            )
            self.notify_listeners()

        def on_turn_completed(turn: DialogueTurn):
            self._archive_turn_audio(turn)
            self.database.save_conversation(self.conversation)
            self.notify_listeners()

        def on_finished():
            self.active_turn_id = None
            self.status_message = self._last_playback_error or "Playback completed"
            self.notify_listeners()

        def on_error(turn: DialogueTurn, error_msg: str):
            if "paid plan" in error_msg.lower():
                self._last_playback_error = self._handle_paid_plan_required()
                self.status_message = self._last_playback_error
                self.notify_listeners()
                return
            self.status_message = f"Error on turn: {error_msg}"
            self.notify_listeners()

        queue.on_turn_started = on_turn_started
        queue.on_turn_completed = on_turn_completed
        queue.on_playback_finished = on_finished
        queue.on_error = on_error

    # ── State Accessors & Actions ─────────────────────────────────────
    @property
    def conversation(self) -> Conversation:
        return self.conversation_manager.current_conversation

    @property
    def speakers(self) -> Dict[str, Speaker]:
        return self.conversation_manager.speakers

    @property
    def devices(self) -> List[AudioDevice]:
        return self.audio_engine.get_devices()

    @property
    def is_playing(self) -> bool:
        return self.conversation_manager.queue.is_playing

    @property
    def is_paused(self) -> bool:
        return self.conversation_manager.queue.is_paused

    def refresh_devices(self) -> None:
        """Refresh PipeWire outputs in the background so the UI stays responsive."""
        if self.is_refreshing_devices:
            return

        self.is_refreshing_devices = True
        self.notify_listeners()

        def worker():
            try:
                devices = self.audio_engine.refresh_devices()
                if devices:
                    valid_ids = {device.id for device in devices}
                    fallback = next((device for device in devices if device.is_default), devices[0])
                    for speaker in self.speakers.values():
                        if speaker.output_device_id and speaker.output_device_id not in valid_ids:
                            speaker.output_device_id = fallback.id
                            self.database.save_speaker(speaker)
                    self.status_message = f"PipeWire outputs synchronized · {len(devices)} found"
                else:
                    # Keep remembered routes if PipeWire is temporarily unavailable.
                    self.status_message = "No PipeWire outputs detected"
            except Exception as exc:
                logger.exception("Could not refresh PipeWire outputs")
                self.status_message = f"Output sync failed: {exc}"
            finally:
                self.is_refreshing_devices = False
                self.notify_listeners()

        threading.Thread(target=worker, name="PipeWireDeviceRefresh", daemon=True).start()

    def update_speaker_device(self, speaker_id: str, device_id: str) -> None:
        speaker = self.conversation_manager.update_speaker(speaker_id=speaker_id, output_device_id=device_id)
        if speaker:
            self.database.save_speaker(speaker)
            self.notify_listeners()

    def update_speaker_voice(self, speaker_id: str, voice_id: str) -> None:
        speaker = self.conversation_manager.update_speaker(speaker_id=speaker_id, voice_id=voice_id)
        if speaker:
            self.database.save_speaker(speaker)
            self._provider_voice_selections.setdefault(self.active_provider, {})[speaker_id] = voice_id
            self._persist_provider_voice_selections()
            for turn in self.conversation.turns:
                if turn.speaker_id != speaker_id:
                    continue
                cached = self._resolve_turn_audio(turn, speaker)
                turn.audio_path = str(cached) if cached else None
                turn.generation_status = GenerationStatus.READY if cached else GenerationStatus.PENDING
            self.database.save_conversation(self.conversation)
            self.notify_listeners()

    def add_turn(self, speaker_id: str, text: str) -> DialogueTurn:
        turn = self.conversation_manager.add_turn(speaker_id=speaker_id, text=text)
        self.database.save_conversation(self.conversation)
        self.notify_listeners()
        return turn

    def update_turn_text(self, turn_id: str, text: str) -> None:
        self.conversation_manager.update_turn_text(turn_id, text)
        self.database.save_conversation(self.conversation)
        self.notify_listeners()

    def remove_turn(self, turn_id: str) -> None:
        self.conversation_manager.remove_turn(turn_id)
        self.database.save_conversation(self.conversation)
        self.notify_listeners()

    # ── Turn Audio Generation & Caching ───────────────────────────────
    def is_turn_cached(self, turn: DialogueTurn) -> bool:
        """Check if audio file exists on disk for this turn."""
        speaker = self.speakers.get(turn.speaker_id)
        if not speaker:
            return False
        cached = self._resolve_turn_audio(turn, speaker)
        if cached:
            turn.audio_path = str(cached)
            turn.generation_status = GenerationStatus.READY
            return True
        return False

    def generate_turn_audio(self, turn_id: str, force: bool = False) -> None:
        """Generate audio for a single dialogue turn in a background worker."""
        if not self._speechify_ready():
            return
        turn = next((t for t in self.conversation.turns if t.id == turn_id), None)
        if not turn:
            return
        speaker = self.speakers.get(turn.speaker_id)
        if not speaker:
            return
        turn.generation_status = GenerationStatus.GENERATING
        self.notify_listeners()

        def worker():
            try:
                turn.generation_status = GenerationStatus.GENERATING
                self.status_message = f"Synthesizing audio for {speaker.name}..."
                self.notify_listeners()

                path = None if force else self._resolve_turn_audio(turn, speaker)
                if path is None:
                    path = self.speech_generator.generate(
                        text=turn.text,
                        voice_id=speaker.voice_id,
                        speaking_rate=speaker.speaking_rate,
                        force_regenerate=force,
                    )
                turn.audio_path = str(path)
                turn.generation_status = GenerationStatus.READY
                self._archive_turn_audio(turn)
                self.database.save_conversation(self.conversation)
                self.status_message = f"Audio ready for {speaker.name}"
            except Exception as e:
                logger.error("Error generating turn audio: %s", e)
                turn.generation_status = GenerationStatus.FAILED
                self.status_message = (
                    self._handle_paid_plan_required()
                    if isinstance(e, PaidPlanRequiredError)
                    else f"Generation error: {e}"
                )
            finally:
                self.notify_listeners()

        threading.Thread(target=worker, daemon=True).start()

    def generate_all_audio(self) -> None:
        """Regenerate audio for every dialogue turn sequentially."""
        self._generate_audio_batch(force=True)

    def generate_uncached_audio(self) -> None:
        """Generate audio only for turns that have no usable cached audio."""
        self._generate_audio_batch(force=False)

    def _generate_audio_batch(self, force: bool) -> None:
        if not self._speechify_ready():
            return
        if self.is_generating:
            return

        self.is_generating = True
        self.status_message = (
            "Regenerating all dialogue audio..."
            if force else "Checking for uncached dialogue audio..."
        )
        self.notify_listeners()

        def worker():
            total = len(self.conversation.turns)
            plan_error = False
            generated_count = 0
            for idx, turn in enumerate(self.conversation.turns):
                speaker = self.speakers.get(turn.speaker_id)
                if not speaker:
                    continue
                try:
                    path = None if force else self._resolve_turn_audio(turn, speaker)
                    if path is None:
                        turn.generation_status = GenerationStatus.GENERATING
                        self.status_message = f"Synthesizing line {idx + 1} of {total}..."
                        self.notify_listeners()
                        path = self.speech_generator.generate(
                            text=turn.text,
                            voice_id=speaker.voice_id,
                            speaking_rate=speaker.speaking_rate,
                            force_regenerate=force,
                        )
                        generated_count += 1
                    turn.audio_path = str(path)
                    turn.generation_status = GenerationStatus.READY
                    self._archive_turn_audio(turn)
                except Exception as e:
                    logger.error("Failed generating turn %s: %s", turn.id, e)
                    turn.generation_status = GenerationStatus.FAILED
                    if isinstance(e, PaidPlanRequiredError):
                        plan_error = True
                        self.status_message = self._handle_paid_plan_required()
                        self.notify_listeners()
                        break

            self.database.save_conversation(self.conversation)
            self.is_generating = False
            if not plan_error:
                self.status_message = (
                    "All dialogue lines regenerated"
                    if force else f"Generated {generated_count} uncached turn(s)"
                )
            self.notify_listeners()

        threading.Thread(target=worker, daemon=True).start()

    def preview_turn(self, turn_id: str) -> None:
        """Play only the selected turn through its assigned audio device."""
        if not self._speechify_ready():
            return
        turn = next((t for t in self.conversation.turns if t.id == turn_id), None)
        if not turn:
            return
        speaker = self.speakers.get(turn.speaker_id)
        if not speaker:
            return
        self.active_turn_id = turn.id
        self.status_message = f"Preparing preview for {speaker.name}"
        self.notify_listeners()

        def worker():
            try:
                current_cache = self._resolve_turn_audio(turn, speaker)
                audio_path = str(current_cache) if current_cache else None
                if not audio_path:
                    path = self.speech_generator.generate(
                        text=turn.text,
                        voice_id=speaker.voice_id,
                        speaking_rate=speaker.speaking_rate,
                    )
                    audio_path = str(path)
                    turn.audio_path = audio_path
                    turn.generation_status = GenerationStatus.READY
                    self._archive_turn_audio(turn)
                    self.database.save_conversation(self.conversation)
                else:
                    turn.audio_path = audio_path
                    turn.generation_status = GenerationStatus.READY
                    self._archive_turn_audio(turn)

                target_device_id = turn.output_device_override or speaker.output_device_id
                target_dev = (
                    self.audio_engine.get_device_by_id(target_device_id)
                    if target_device_id
                    else self.audio_engine.get_default_device()
                )
                self.active_turn_id = turn.id
                dev_name = target_dev.name if target_dev else "Default"
                self.status_message = f"Preview: {speaker.name} -> {dev_name}"
                self.notify_listeners()

                handle = self.audio_engine.play(audio_path=audio_path, device_id=target_dev.id if target_dev else None)
                import time
                while handle.status not in (PlaybackStatus.COMPLETED, PlaybackStatus.STOPPED, PlaybackStatus.ERROR):
                    time.sleep(0.05)

            except Exception as e:
                logger.error("Error previewing turn: %s", e)
                self.status_message = (
                    self._handle_paid_plan_required()
                    if isinstance(e, PaidPlanRequiredError)
                    else f"Preview error: {e}"
                )
            finally:
                self.active_turn_id = None
                self.notify_listeners()

        threading.Thread(target=worker, daemon=True).start()

    # ── Playback Controls ─────────────────────────────────────────────
    def play(self) -> None:
        if not self._speechify_ready():
            return
        self._last_playback_error = None
        self.status_message = "Starting playback..."
        self.conversation_manager.play_conversation()
        self.notify_listeners()

    def pause(self) -> None:
        self.conversation_manager.pause_playback()
        self.status_message = "Paused"
        self.notify_listeners()

    def resume(self) -> None:
        self.conversation_manager.resume_playback()
        self.status_message = "Resumed"
        self.notify_listeners()

    def stop(self) -> None:
        self.conversation_manager.stop_playback()
        self.active_turn_id = None
        self.status_message = "Stopped"
        self.notify_listeners()
