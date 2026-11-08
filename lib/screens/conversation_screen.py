# ── Imports & Framework Dependencies ───────────────────────────────────
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import QFileDialog
from pythra.base import Key
from pythra.styles import (
    BorderRadius,
    BorderSide,
    ButtonStyle,
    CrossAxisAlignment,
    EdgeInsets,
    InputDecoration,
    TextStyle,
    MainAxisAlignment,
)
from pythra.widgets import SizedBox
from pythra import (
    Column,
    Container,
    ElevatedButton,
    Expanded,
    Framework,
    SingleChildScrollView,
    Row,
    State,
    StatefulWidget,
    Text,
    dispatch_to_main,
)
from ..constants.colors import StudioColors
from ..conversation.models import GenerationStatus
from ..components import (
    build_conversation_bubble,
    build_dialogue_editor,
    build_heading,
    build_playback_controls,
    build_speaker_card,
)
from ..state.app_state import AppState


# ── Conversation Studio Screen State ──────────────────────────────────
class ConversationScreenState(State):
    """
    Reactive state controller for the primary Conversation Studio view.
    Subscribes to AppState events and supports in-line turn editing,
    audio pre-generation, device targeting, and voice selection.
    """

    def __init__(self):
        super().__init__()
        self.app_state = AppState.get()
        self.editing_turn_id: Optional[str] = None
        # Bind Pythra setState to AppState updates
        self.app_state.add_listener(self._on_app_state_change)

    def _on_app_state_change(self):
        # PyThra hot reload can replace the screen widget while retaining old
        # listeners. Drop callbacks whose weak widget reference is no longer live.
        if self.get_widget() is None:
            self.app_state.remove_listener(self._on_app_state_change)
            return
        # WebChannel callbacks and background catalog/audio workers may notify
        # from different threads. Reconciliation must run on Qt's UI thread.
        dispatch_to_main(self._refresh_screen)

    def _refresh_screen(self):
        if self.get_widget() is not None:
            self.setState()

    def dispose(self):
        self.app_state.remove_listener(self._on_app_state_change)

    # ── User Actions ──────────────────────────────────────────────────
    def on_refresh_devices(self):
        self.app_state.refresh_devices()

    def on_select_conversation(self, conversation_id):
        if conversation_id:
            loaded = self.app_state.load_conversation(str(conversation_id))
            if not loaded:
                self.app_state.status_message = "Could not load the selected conversation."
                self.app_state.notify_listeners()

    def _load_bundled_json(self, conversation_id: str):
        """Use the same import-and-activate path as the working Import JSON action."""
        source = Path(__file__).resolve().parent.parent.parent / "conversations" / f"{conversation_id}.json"
        try:
            self.app_state.import_conversation_json(source, reuse_existing=True)
        except Exception as exc:
            self.app_state.status_message = f"Could not load conversation: {exc}"
            self.app_state.notify_listeners()

    def on_load_conversation_01(self):
        self._load_bundled_json("conversation_01")

    def on_load_conversation_02(self):
        self._load_bundled_json("conversation_02")

    def on_load_conversation_03(self):
        self._load_bundled_json("conversation_03")

    def on_import_conversation(self):
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Import 11Voice Conversation",
            str(Path(__file__).resolve().parent.parent.parent / "conversations"),
            "Conversation JSON (*.json)",
        )
        if not path:
            return
        try:
            self.app_state.import_conversation_json(path)
        except Exception as exc:
            self.app_state.status_message = f"Could not import conversation: {exc}"
            self.app_state.notify_listeners()

    def on_speaker_device_changed(self, speaker_id: str, device_id: str):
        self.app_state.update_speaker_device(speaker_id, device_id)

    def on_speaker_voice_changed(self, speaker_id: str, voice_id: str):
        self.app_state.update_speaker_voice(speaker_id, voice_id)

    def on_start_edit_turn(self, turn_id: str):
        self.editing_turn_id = turn_id
        self.setState()

    def on_cancel_edit_turn(self):
        self.editing_turn_id = None
        self.setState()

    def on_save_edit_turn(self, turn_id: str, new_text: str, new_speaker_id: str):
        self.app_state.update_turn_text(turn_id, new_text)
        turn = next((t for t in self.app_state.conversation.turns if t.id == turn_id), None)
        if turn and turn.speaker_id != new_speaker_id:
            turn.speaker_id = new_speaker_id
            turn.audio_path = None
            turn.generation_status = GenerationStatus.PENDING
            self.app_state.database.save_conversation(self.app_state.conversation)
        self.editing_turn_id = None
        self.setState()

    def on_add_turn(self):
        speaker_ids = list(dict.fromkeys(turn.speaker_id for turn in self.app_state.conversation.turns))
        if not speaker_ids:
            speaker_ids = [sid for sid in ("spk_a", "spk_b") if sid in self.app_state.speakers]
        speakers = [self.app_state.speakers[sid] for sid in speaker_ids if sid in self.app_state.speakers]
        if not speakers:
            return
        turns = self.app_state.conversation.turns
        next_speaker = speakers[0]
        if turns:
            last_speaker_id = turns[-1].speaker_id
            for spk in speakers:
                if spk.id != last_speaker_id:
                    next_speaker = spk
                    break

        new_turn_text = f"Dialogue line {len(turns) + 1} from {next_speaker.name}."
        new_turn = self.app_state.add_turn(next_speaker.id, new_turn_text)
        # Automatically open editor for new turn
        self.editing_turn_id = new_turn.id
        self.setState()

    def on_delete_turn(self, turn_id: str):
        if self.editing_turn_id == turn_id:
            self.editing_turn_id = None
        self.app_state.remove_turn(turn_id)

    # ── UI Tree Build ─────────────────────────────────────────────────
    def build(self):
        active_speaker_ids = list(dict.fromkeys(turn.speaker_id for turn in self.app_state.conversation.turns))
        if not active_speaker_ids:
            active_speaker_ids = [sid for sid in ("spk_a", "spk_b") if sid in self.app_state.speakers]
        speakers = {
            speaker_id: self.app_state.speakers[speaker_id]
            for speaker_id in active_speaker_ids
            if speaker_id in self.app_state.speakers
        }
        devices = self.app_state.devices
        conversation_items = self.app_state.database.list_conversations()
        current_conversation_id = self.app_state.conversation.id
        featured_actions = (
            ("conversation_01", self.on_load_conversation_01),
            ("conversation_02", self.on_load_conversation_02),
            ("conversation_03", self.on_load_conversation_03),
        )
        framework = Framework.instance()
        if framework and getattr(framework, "api", None):
            for _, action in featured_actions:
                framework.api.register_callback(action.__name__, action)
        conversation_titles = dict(conversation_items)
        featured_conversations = [
            (conversation_id, conversation_titles[conversation_id], action)
            for conversation_id, action in featured_actions
            if conversation_id in conversation_titles
        ]
        speaker_cards = []
        speaker_accents = [StudioColors.speaker_a, StudioColors.speaker_b]

        for idx, (spk_id, speaker) in enumerate(speakers.items()):
            accent = speaker_accents[idx % len(speaker_accents)]
            
            speaker_cards.append(
                Container(
                    key=Key(f"spk_exp_{spk_id}"),
                    child=build_speaker_card(
                        speaker=speaker,
                        devices=devices,
                        accent_color=accent,
                        available_voices=self.app_state.available_voices,
                        on_device_selected=lambda d_id, s_id=spk_id: self.on_speaker_device_changed(s_id, d_id),
                        on_voice_selected=lambda v_id, s_id=spk_id: self.on_speaker_voice_changed(s_id, v_id),
                    ),
                )
            )
            if idx < len(speakers) - 1:
                speaker_cards.append(SizedBox(width=16, key=Key(f"spk_gap_{spk_id}")))

        # Build turn bubbles or in-line editors
        turn_widgets = []
        for turn in self.app_state.conversation.turns:
            if turn.id == self.editing_turn_id:
                # Render in-line editor
                turn_widgets.append(
                    build_dialogue_editor(
                        turn=turn,
                        speakers=speakers,
                        on_save=lambda txt, s_id, t_id=turn.id: self.on_save_edit_turn(t_id, txt, s_id),
                        on_cancel=self.on_cancel_edit_turn,
                    )
                )
            else:
                speaker = speakers.get(turn.speaker_id)
                if not speaker:
                    continue
                is_active = (turn.id == self.app_state.active_turn_id)
                is_cached = self.app_state.is_turn_cached(turn)
                is_generating = (turn.generation_status == GenerationStatus.GENERATING)
                dev = self.app_state.audio_engine.get_device_by_id(speaker.output_device_id)
                dev_label = dev.name if dev else "Default Sink"
                spk_idx = list(speakers.keys()).index(speaker.id) if speaker.id in speakers else 0
                accent = speaker_accents[spk_idx % len(speaker_accents)]

                turn_widgets.append(
                    build_conversation_bubble(
                        turn=turn,
                        speaker=speaker,
                        is_active=is_active,
                        is_cached=is_cached,
                        is_generating=is_generating,
                        device_label=dev_label,
                        accent_color=accent,
                        on_preview=lambda t_id=turn.id: self.app_state.preview_turn(t_id),
                        on_generate=lambda t_id=turn.id: self.app_state.generate_turn_audio(t_id, force=True),
                        on_edit=lambda t_id=turn.id: self.on_start_edit_turn(t_id),
                        on_delete=lambda t_id=turn.id: self.on_delete_turn(t_id),
                    )
                )
            turn_widgets.append(SizedBox(height=12, key=Key(f"turn_gap_{turn.id}")))

        if not turn_widgets:
            turn_widgets.append(
                Container(
                    key=Key("empty_turns_notice"),
                    padding=EdgeInsets.all(32),
                    child=Text(
                        "No dialogue turns yet. Click '+ Add Turn' to start the script.",
                        style=TextStyle(color=StudioColors.text_muted, fontSize=14),
                    ),
                )
            )

        return Container(
            key=Key("studio_root_view"),
            height="100vh",
            width="100vw",
            color=StudioColors.background,
            child=Column(
                key=Key("studio_main_column"),
                children=[
                    # ── Header ────────────────────────────────────────
                    build_heading(
                        title="11Voice Conversation Studio",
                        on_refresh_devices=self.on_refresh_devices,
                    ),

                    # ── Conversation Library ─────────────────────────
                    Container(
                        key=Key("conversation_library_bar"),
                        padding=EdgeInsets.symmetric(horizontal=20, vertical=10),
                        width="-webkit-fill-available",
                        child=Row(
                            key=Key("conversation_library_row"),
                            crossAxisAlignment=CrossAxisAlignment.CENTER,
                            children=[
                                Text(
                                    "Conversation",
                                    key=Key("conversation_library_label"),
                                    style=TextStyle(color=StudioColors.text_primary, fontSize=13, fontWeight="bold"),
                                ),
                                SizedBox(width=12, key=Key("conversation_library_gap")),
                                    *[
                                    ElevatedButton(
                                        key=Key(f"load_conversation_{conversation_id}"),
                                            onPressed=action,
                                        style=ButtonStyle(
                                            backgroundColor=(
                                                StudioColors.primary
                                                if current_conversation_id == conversation_id
                                                else StudioColors.surface_elevated
                                            ),
                                            foregroundColor=StudioColors.text_primary,
                                            padding=EdgeInsets.symmetric(horizontal=10, vertical=10),
                                            shape=BorderRadius.circular(8),
                                        ),
                                        child=Text(
                                            conversation_titles[conversation_id],
                                            style=TextStyle(fontSize=12, fontWeight="bold"),
                                        ),
                                    )
                                        for conversation_id, _, action in featured_conversations
                                ],
                                SizedBox(width=12, key=Key("conversation_import_gap")),
                                ElevatedButton(
                                    key=Key("conversation_import_json_btn"),
                                    onPressed=self.on_import_conversation,
                                    onPressedName="import_conversation_json",
                                    style=ButtonStyle(
                                        backgroundColor=StudioColors.surface_elevated,
                                        foregroundColor=StudioColors.text_primary,
                                        padding=EdgeInsets.symmetric(horizontal=14, vertical=10),
                                        shape=BorderRadius.circular(8),
                                    ),
                                    child=Text("Import JSON", style=TextStyle(fontSize=13, fontWeight="bold")),
                                ),
                            ],
                        ),
                    ),

                    # ── Speaker Output Routing Deck ───────────────────
                    Container(
                        key=Key("speakers_deck"),
                        padding=EdgeInsets.all(16),
                        width='-webkit-fill-available',
                        child=Row(
                            mainAxisAlignment=MainAxisAlignment.SPACE_AROUND,
                            key=Key("speakers_row"),
                            children=speaker_cards,
                        ),
                    ),

                    # ── Dialogue Script Timeline ──────────────────────
                    Expanded(
                        key=Key("timeline_expanded"),
                        child=SingleChildScrollView(
                            key=Key("timeline_scroll"),
                            padding=EdgeInsets.symmetric(horizontal=16, vertical=8),
                            child=Column(
                                key=Key("timeline_col"),
                                crossAxisAlignment=CrossAxisAlignment.STRETCH,
                                children=turn_widgets,
                            ),
                        ),
                    ),

                    # ── Playback Controls Toolbar ─────────────────────
                    build_playback_controls(
                        is_playing=self.app_state.is_playing,
                        is_paused=self.app_state.is_paused,
                        is_generating=self.app_state.is_generating,
                        status_text=self.app_state.status_message,
                        on_play=self.app_state.play,
                        on_pause=self.app_state.pause,
                        on_stop=self.app_state.stop,
                        on_generate_all=self.app_state.generate_all_audio,
                        on_add_turn=self.on_add_turn,
                    ),
                ],
            ),
        )


# ── Conversation Studio Screen Widget ─────────────────────────────────
class ConversationScreen(StatefulWidget):
    """Root Conversation Studio application screen widget."""

    def __init__(self, key=Key("conversation_screen_widget")):
        super().__init__(key=key)

    def createState(self):
        return ConversationScreenState()
