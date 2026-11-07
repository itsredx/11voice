# ── Imports & Framework Dependencies ───────────────────────────────────
from typing import Optional
from pythra.base import Key
from pythra.styles import (
    CrossAxisAlignment,
    EdgeInsets,
    TextStyle,
    MainAxisAlignment,
)
from pythra.widgets import SizedBox
from pythra import (
    Column,
    Container,
    Expanded,
    SingleChildScrollView,
    Row,
    State,
    StatefulWidget,
    Text,
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
        self.setState()

    # ── User Actions ──────────────────────────────────────────────────
    def on_refresh_devices(self):
        self.app_state.refresh_devices()

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
            self.app_state.database.save_conversation(self.app_state.conversation)
        self.editing_turn_id = None
        self.setState()

    def on_add_turn(self):
        speakers = list(self.app_state.speakers.values())
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
        speakers = self.app_state.speakers
        devices = self.app_state.devices
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
