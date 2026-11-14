# ── Imports & Framework Dependencies ───────────────────────────────────
import json
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
from pythra.widgets import (
    SizedBox,
    VirtualListController,
    VirtualListView,
    _VirtualListViewState,
)
from pythra.controllers import TextEditingController
from pythra import (
    Column,
    Container,
    ElevatedButton,
    Expanded,
    Framework,
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
    build_provider_settings,
)
from ..state.app_state import AppState


class _ConversationTurnListState(_VirtualListViewState):
    """Keep one virtual-list DOM instance and update its data in place."""

    def initState(self):
        super().initState()
        self._initial_virtualization_options = dict(self._virtualization_options or {})

    def didUpdateWidget(self, oldWidget, newWidget):
        super().didUpdateWidget(oldWidget, newWidget)
        data_changed = (
            oldWidget.conversation_id != newWidget.conversation_id
            or oldWidget.itemCount != newWidget.itemCount
            or oldWidget.itemExtent != newWidget.itemExtent
        )
        if not data_changed:
            return

        self._virtualization_options = {
            "type": "list",
            "itemCount": newWidget.itemCount,
            "itemExtent": newWidget.itemExtent,
            "itemBuilderName": self.item_builder_name,
            "initialItems": {},
        }
        if not (self.framework and self.framework.window):
            return

        instance_name = json.dumps(f"{newWidget.key.value}_vlist")
        item_count = newWidget.itemCount
        item_extent = newWidget.itemExtent
        sizer_height = item_count * item_extent
        reset_scroll = oldWidget.conversation_id != newWidget.conversation_id
        script = f"""
            (() => {{
                const list = window._pythra_instances?.[{instance_name}];
                if (!list) return;
                const oldExtent = Math.max(1, list.options.itemExtent);
                const oldScrollTop = list.scrollEl.scrollTop;
                list.options.itemCount = {item_count};
                list.options.itemExtent = {item_extent};
                list.sizer.style.height = '{sizer_height}px';
                const nextScrollTop = {"0" if reset_scroll else f"oldScrollTop * {item_extent} / oldExtent"};
                list.scrollEl.scrollTop = Math.max(
                    0,
                    Math.min(nextScrollTop, {sizer_height} - list.scrollEl.clientHeight)
                );
                list.visibleItemElements.forEach((element) => {{
                    element.style.height = '{item_extent}px';
                }});
                list.refresh();
            }})();
        """
        self.framework.window.evaluate_js(self.framework.id, script)

    def build(self):
        # Keep the Scrollbar initializer props stable. didUpdateWidget updates
        # the live JS list above, so reconciliation must not create another one.
        current_options = self._virtualization_options
        self._virtualization_options = self._initial_virtualization_options
        try:
            return super().build()
        finally:
            self._virtualization_options = current_options


class _ConversationTurnList(VirtualListView):
    def __init__(self, conversation_id: str, **kwargs):
        self.conversation_id = conversation_id
        super().__init__(**kwargs)

    def createState(self):
        return _ConversationTurnListState()


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
        self.turn_list_controller = VirtualListController()
        self._last_turn_signature = None
        self._last_controls_signature = None
        self._last_turn_list_config = None
        self._last_active_turn_id = None
        self.show_settings = False
        self.elevenlabs_key_controller = TextEditingController()
        self.speechify_key_controller = TextEditingController()
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
            active_turn_id = self.app_state.active_turn_id
            if active_turn_id != self._last_active_turn_id:
                self._last_active_turn_id = active_turn_id
                if active_turn_id:
                    active_index = next(
                        (
                            index
                            for index, turn in enumerate(
                                self.app_state.conversation.turns
                            )
                            if turn.id == active_turn_id
                        ),
                        None,
                    )
                    if active_index is not None:
                        self.turn_list_controller.scrollToIndex(
                            active_index,
                            alignment="center",
                            behavior="smooth",
                        )

            turn_signature = self._get_turn_signature()
            previous_turn_signature = self._last_turn_signature
            turn_list_config = self._get_turn_list_config()
            previous_turn_list_config = self._last_turn_list_config
            self._last_turn_signature = turn_signature
            self._last_turn_list_config = turn_list_config

            # A structural list update already invalidates all visible rows in
            # _ConversationTurnListState.didUpdateWidget. Avoid racing it with
            # per-row refresh requests for the same conversation switch.
            if (
                previous_turn_signature is not None
                and previous_turn_list_config == turn_list_config
            ):
                changed_indices = [
                    index
                    for index in range(
                        max(len(previous_turn_signature), len(turn_signature))
                    )
                    if index >= len(previous_turn_signature)
                    or index >= len(turn_signature)
                    or previous_turn_signature[index] != turn_signature[index]
                ]
                for index in changed_indices:
                    if index < len(turn_signature):
                        self.turn_list_controller.refreshItem(index)

            controls_signature = self._get_controls_signature()
            if controls_signature != self._last_controls_signature:
                self._last_controls_signature = controls_signature
                self.setState()

    def _get_turn_signature(self):
        """Capture only the values rendered inside each virtualized row."""
        signature = []
        devices_by_id = {device.id: device for device in self.app_state.devices}
        for turn in self.app_state.conversation.turns:
            speaker = self.app_state.speakers.get(turn.speaker_id)
            device = devices_by_id.get(speaker.output_device_id) if speaker else None
            signature.append(
                (
                    turn.id,
                    turn.text,
                    turn.speaker_id,
                    turn.generation_status,
                    turn.audio_path,
                    turn.id == self.app_state.active_turn_id,
                    speaker.name if speaker else None,
                    device.name if device else "Default Sink",
                    turn.id == self.editing_turn_id,
                )
            )
        return tuple(signature)

    def _get_turn_list_config(self):
        turns = self.app_state.conversation.turns
        longest_turn = max((len(turn.text) for turn in turns), default=0)
        estimated_lines = max(1, (longest_turn + 39) // 40)
        item_extent = 92 + estimated_lines * 22
        if self.editing_turn_id:
            item_extent += 120
        return (
            self.app_state.conversation.id,
            max(1, len(turns)),
            item_extent,
        )

    def _get_controls_signature(self):
        speaker_signature = tuple(
            (sid, speaker.name, speaker.voice_id, speaker.output_device_id)
            for sid, speaker in self.app_state.speakers.items()
        )
        device_signature = tuple(
            (device.id, device.name) for device in self.app_state.devices
        )
        return (
            self.app_state.conversation.id,
            len(self.app_state.conversation.turns),
            self.app_state.is_playing,
            self.app_state.is_paused,
            self.app_state.is_generating,
            self.app_state.is_refreshing_devices,
            self.app_state.status_message,
            self.app_state.active_provider,
            tuple(voice.voice_id for voice in self.app_state.available_voices),
            self.show_settings,
            speaker_signature,
            device_signature,
        )

    def dispose(self):
        self.app_state.remove_listener(self._on_app_state_change)

    # ── User Actions ──────────────────────────────────────────────────
    def on_refresh_devices(self):
        self.app_state.refresh_devices()

    def on_switch_provider(self):
        self.app_state.switch_provider()

    def on_open_settings(self):
        self.show_settings = True
        self.setState()

    def on_close_settings(self):
        self.show_settings = False
        self.setState()

    def on_save_provider_key(self, provider: str, value: str):
        if not value.strip():
            return
        self.app_state.save_provider_api_key(provider, value)
        (
            self.elevenlabs_key_controller
            if provider == "elevenlabs"
            else self.speechify_key_controller
        ).clear()

    def on_remove_provider_key(self, provider: str):
        self.app_state.save_provider_api_key(provider, "")
        (
            self.elevenlabs_key_controller
            if provider == "elevenlabs"
            else self.speechify_key_controller
        ).clear()

    def on_select_conversation(self, conversation_id):
        if conversation_id:
            loaded = self.app_state.load_conversation(str(conversation_id))
            if not loaded:
                self.app_state.status_message = (
                    "Could not load the selected conversation."
                )
                self.app_state.notify_listeners()

    def _load_bundled_json(self, conversation_id: str):
        """Use the same import-and-activate path as the working Import JSON action."""
        source = (
            Path(__file__).resolve().parent.parent.parent
            / "conversations"
            / f"{conversation_id}.json"
        )
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
        turn = next(
            (t for t in self.app_state.conversation.turns if t.id == turn_id), None
        )
        if turn and turn.speaker_id != new_speaker_id:
            turn.speaker_id = new_speaker_id
            turn.audio_path = None
            turn.generation_status = GenerationStatus.PENDING
            self.app_state.database.save_conversation(self.app_state.conversation)
        self.editing_turn_id = None
        self.setState()

    def on_add_turn(self):
        speaker_ids = list(
            dict.fromkeys(turn.speaker_id for turn in self.app_state.conversation.turns)
        )
        if not speaker_ids:
            speaker_ids = [
                sid for sid in ("spk_a", "spk_b") if sid in self.app_state.speakers
            ]
        speakers = [
            self.app_state.speakers[sid]
            for sid in speaker_ids
            if sid in self.app_state.speakers
        ]
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
        if self.show_settings:
            return Container(
                key=Key("provider_settings_root"),
                height="100vh",
                width="100vw",
                color=StudioColors.background,
                child=build_provider_settings(
                    elevenlabs_controller=self.elevenlabs_key_controller,
                    speechify_controller=self.speechify_key_controller,
                    has_elevenlabs_key=self.app_state.has_provider_api_key(
                        "elevenlabs"
                    ),
                    has_speechify_key=self.app_state.has_provider_api_key("speechify"),
                    on_save_key=self.on_save_provider_key,
                    on_remove_key=self.on_remove_provider_key,
                    on_back=self.on_close_settings,
                ),
            )
        active_speaker_ids = list(
            dict.fromkeys(turn.speaker_id for turn in self.app_state.conversation.turns)
        )
        if not active_speaker_ids:
            active_speaker_ids = [
                sid for sid in ("spk_a", "spk_b") if sid in self.app_state.speakers
            ]
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
        devices_by_id = {device.id: device for device in devices}

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
                        provider=self.app_state.active_provider,
                        on_device_selected=lambda d_id, s_id=spk_id: self.on_speaker_device_changed(
                            s_id, d_id
                        ),
                        on_voice_selected=lambda v_id, s_id=spk_id: self.on_speaker_voice_changed(
                            s_id, v_id
                        ),
                    ),
                )
            )
            if idx < len(speakers) - 1:
                speaker_cards.append(SizedBox(width=16, key=Key(f"spk_gap_{spk_id}")))

        turns = self.app_state.conversation.turns

        def build_turn_item(index: int):
            current_turns = self.app_state.conversation.turns
            if not current_turns:
                return Container(
                    key=Key("empty_turn_item"),
                    height=turn_item_extent,
                    padding=EdgeInsets.all(32),
                    child=Text(
                        "No dialogue turns yet. Click '+ Add Turn' to start the script.",
                        style=TextStyle(color=StudioColors.text_muted, fontSize=14),
                    ),
                )
            if index >= len(current_turns):
                return Container(
                    key=Key(f"turn_item_empty_{index}"), height=turn_item_extent
                )
            turn = current_turns[index]
            if turn.id == self.editing_turn_id:
                content = build_dialogue_editor(
                    turn=turn,
                    speakers=speakers,
                    on_save=lambda txt, s_id, t_id=turn.id: self.on_save_edit_turn(
                        t_id, txt, s_id
                    ),
                    on_cancel=self.on_cancel_edit_turn,
                )
            else:
                speaker = self.app_state.speakers.get(turn.speaker_id)
                if not speaker:
                    return Container(
                        key=Key(f"turn_item_missing_{turn.id}"), height=turn_item_extent
                    )
                is_active = turn.id == self.app_state.active_turn_id
                is_cached = self.app_state.is_turn_cached(turn)
                is_generating = turn.generation_status == GenerationStatus.GENERATING
                dev = devices_by_id.get(speaker.output_device_id)
                dev_label = dev.name if dev else "Default Sink"
                speaker_ids = list(speakers.keys())
                spk_idx = (
                    speaker_ids.index(speaker.id) if speaker.id in speaker_ids else 0
                )
                content = build_conversation_bubble(
                    turn=turn,
                    speaker=speaker,
                    is_active=is_active,
                    is_cached=is_cached,
                    is_generating=is_generating,
                    device_label=dev_label,
                    accent_color=speaker_accents[spk_idx % len(speaker_accents)],
                    on_preview=lambda t_id=turn.id: self.app_state.preview_turn(t_id),
                    on_generate=lambda t_id=turn.id: self.app_state.generate_turn_audio(
                        t_id, force=True
                    ),
                    on_edit=lambda t_id=turn.id: self.on_start_edit_turn(t_id),
                    on_delete=lambda t_id=turn.id: self.on_delete_turn(t_id),
                )
            return Container(
                key=Key(f"turn_item_{turn.id}"),
                height=turn_item_extent,
                width="-webkit-fill-available",
                padding=EdgeInsets.symmetric(horizontal=16, vertical=6),
                child=content,
            )

        # VirtualListView requires one fixed extent. Size every row for the
        # longest turn at a narrow desktop width so dialogue remains untruncated.
        longest_turn = max((len(turn.text) for turn in turns), default=0)
        estimated_lines = max(1, (longest_turn + 39) // 40)
        turn_item_extent = 92 + estimated_lines * 22
        turn_item_extent = min(turn_item_extent, 168)
        if self.editing_turn_id:
            turn_item_extent += 120

        timeline = _ConversationTurnList(
            conversation_id=self.app_state.conversation.id,
            key=Key("conversation_turns"),
            controller=self.turn_list_controller,
            itemCount=max(1, len(turns)),
            itemBuilder=build_turn_item,
            itemExtent=turn_item_extent,
            initialItemCount=min(5, max(1, len(turns))),
            width="100%",
            height="100%",
        )

        self._last_turn_signature = self._get_turn_signature()
        self._last_turn_list_config = self._get_turn_list_config()
        self._last_controls_signature = self._get_controls_signature()

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
                        is_syncing_outputs=self.app_state.is_refreshing_devices,
                        active_provider=self.app_state.active_provider,
                        on_switch_provider=self.on_switch_provider,
                        on_open_settings=self.on_open_settings,
                    ),
                    # ── Conversation Library ─────────────────────────
                    Container(
                        key=Key("conversation_library_bar"),
                        padding=EdgeInsets.symmetric(horizontal=20, vertical=10),
                        width="-webkit-fill-available",
                        child=Row(
                            key=Key("conversation_library_and_action_row"),
                            crossAxisAlignment=CrossAxisAlignment.CENTER,
                            mainAxisAlignment=MainAxisAlignment.SPACE_BETWEEN,
                            children=[
                                Text(
                                    "Conversations",
                                    key=Key("conversation_library_label"),
                                    style=TextStyle(
                                        color=StudioColors.text_primary,
                                        fontSize=13,
                                        fontWeight="bold",
                                    ),
                                ),
                                SizedBox(width=12, key=Key("conversation_library_gap")),
                                Row(
                                    key=Key("conversation_library_row"),
                                    crossAxisAlignment=CrossAxisAlignment.CENTER,
                                    children=[
                                        *[
                                            ElevatedButton(
                                                key=Key(
                                                    f"load_conversation_{conversation_id}"
                                                ),
                                                onPressed=action,
                                                tooltip=f"Load conversation: {conversation_titles[conversation_id]}",
                                                style=ButtonStyle(
                                                    backgroundColor=(
                                                        StudioColors.primary
                                                        if current_conversation_id
                                                        == conversation_id
                                                        else StudioColors.surface_elevated
                                                    ),
                                                    foregroundColor=StudioColors.text_primary,
                                                    padding=EdgeInsets.symmetric(
                                                        horizontal=10, vertical=10
                                                    ),
                                                    shape=BorderRadius.circular(8),
                                                    minimumSize=(155, 40),
                                                ),
                                                child=Text(
                                                    conversation_titles[
                                                        conversation_id
                                                    ],
                                                    style=TextStyle(
                                                        fontSize=12, fontWeight="bold"
                                                    ),
                                                ),
                                            )
                                            for conversation_id, _, action in featured_conversations
                                        ],
                                    ],
                                ),
                                SizedBox(width=12, key=Key("conversation_import_gap")),
                                ElevatedButton(
                                    key=Key("conversation_import_json_btn"),
                                    onPressed=self.on_import_conversation,
                                    onPressedName="import_conversation_json",
                                    tooltip="Import a conversation from a JSON file",
                                    style=ButtonStyle(
                                        backgroundColor=StudioColors.surface_elevated,
                                        foregroundColor=StudioColors.text_primary,
                                        padding=EdgeInsets.symmetric(
                                            horizontal=14, vertical=10
                                        ),
                                        shape=BorderRadius.circular(8),
                                        minimumSize=(150, 40),
                                    ),
                                    child=Text(
                                        "Import JSON",
                                        style=TextStyle(fontSize=13, fontWeight="bold"),
                                    ),
                                ),
                            ],
                        ),
                    ),
                    # ── Speaker Output Routing Deck ───────────────────
                    Container(
                        key=Key("speakers_deck"),
                        padding=EdgeInsets.all(16),
                        width="-webkit-fill-available",
                        child=Row(
                            mainAxisAlignment=MainAxisAlignment.SPACE_AROUND,
                            key=Key("speakers_row"),
                            children=speaker_cards,
                        ),
                    ),
                    # ── Dialogue Script Timeline ──────────────────────
                    Expanded(
                        key=Key("timeline_expanded"),
                        child=timeline,
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
                        on_generate_uncached=self.app_state.generate_uncached_audio,
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
