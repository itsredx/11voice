# ── Imports & Setup ──────────────────────────────────────────────────
from typing import Callable, Dict, Optional
from pythra.base import Key
from pythra.controllers import TextEditingController
from pythra.styles import (
    BorderRadius,
    BorderSide,
    BoxDecoration,
    ButtonStyle,
    CrossAxisAlignment,
    EdgeInsets,
    InputDecoration,
    MainAxisAlignment,
    TextStyle,
)
from pythra.widgets import SizedBox
from pythra import (
    Column,
    Container,
    ElevatedButton,
    Icon,
    Icons,
    Row,
    Text,
    TextButton,
    TextField,
)
from ..constants.colors import StudioColors
from ..conversation.models import DialogueTurn, Speaker


# ── In-line Dialogue Editor Component ──────────────────────────────────
def build_dialogue_editor(
    turn: DialogueTurn,
    speakers: Dict[str, Speaker],
    on_save: Callable[[str, str], None],
    on_cancel: Callable[[], None],
    controller: Optional[TextEditingController] = None,
):
    """
    In-line editor for a dialogue turn allowing text revisions and speaker reassignment.
    Automatically flags the turn as PENDING to invalidate stale audio cache.
    """
    text_ctrl = controller or TextEditingController(text=turn.text)
    selected_speaker_id = turn.speaker_id

    speaker_toggle_buttons = []
    for spk_id, spk in speakers.items():
        is_selected = (spk_id == selected_speaker_id)
        btn_bg = StudioColors.primary if is_selected else StudioColors.surface_elevated
        
        speaker_toggle_buttons.append(
            ElevatedButton(
                key=Key(f"edit_spk_btn_{turn.id}_{spk_id}"),
                onPressed=lambda s_id=spk_id: on_save(text_ctrl.text, s_id),
                onPressedName=f"select_spk_{turn.id}_{spk_id}",
                tooltip=f"Assign this turn to {spk.name}",
                style=ButtonStyle(
                    backgroundColor=btn_bg,
                    foregroundColor=StudioColors.text_primary,
                    padding=EdgeInsets.symmetric(horizontal=12, vertical=6),
                    shape=BorderRadius.circular(4),
                ),
                child=Text(
                    spk.name,
                    style=TextStyle(fontSize=11, fontWeight="bold"),
                ),
            )
        )
        speaker_toggle_buttons.append(SizedBox(width=8, key=Key(f"edit_spc_{turn.id}_{spk_id}")))

    return Container(
        key=Key(f"turn_editor_container_{turn.id}"),
        padding=EdgeInsets.all(16),
        decoration=BoxDecoration(
            color=StudioColors.surface_elevated,
            borderRadius=BorderRadius.circular(10),
        ),
        child=Column(
            key=Key(f"turn_editor_col_{turn.id}"),
            crossAxisAlignment=CrossAxisAlignment.START,
            children=[
                # ── Header & Speaker Assignment ───────────────────────
                Row(
                    key=Key(f"editor_hdr_{turn.id}"),
                    mainAxisAlignment=MainAxisAlignment.SPACE_BETWEEN,
                    crossAxisAlignment=CrossAxisAlignment.CENTER,
                    children=[
                        Text(
                            "Editing Dialogue Turn",
                            key=Key(f"editor_title_{turn.id}"),
                            style=TextStyle(
                                fontSize=13,
                                fontWeight="bold",
                                color=StudioColors.primary,
                            ),
                        ),
                        Row(
                            key=Key(f"editor_speakers_row_{turn.id}"),
                            crossAxisAlignment=CrossAxisAlignment.CENTER,
                            children=speaker_toggle_buttons,
                        ),
                    ],
                ),
                SizedBox(height=12, key=Key(f"editor_spc_1_{turn.id}")),

                # ── Text Field Input ──────────────────────────────────
                TextField(
                    key=Key(f"turn_textfield_{turn.id}"),
                    controller=text_ctrl,
                    decoration=InputDecoration(
                        hintText="Enter dialogue text for this turn...",
                        filled=True,
                        fillColor=StudioColors.surface,
                        contentPadding=EdgeInsets.all(12),
                        borderRadius=BorderRadius.circular(8),
                        border=BorderSide(color=StudioColors.border, width=1),
                        inputStyle=TextStyle(
                            fontSize=14,
                            color=StudioColors.text_primary,
                            lineHeight=1.4,
                        ),
                    ),
                ),
                SizedBox(height=12, key=Key(f"editor_spc_2_{turn.id}")),

                # ── Action Buttons ────────────────────────────────────
                Row(
                    key=Key(f"editor_actions_row_{turn.id}"),
                    mainAxisAlignment=MainAxisAlignment.END,
                    crossAxisAlignment=CrossAxisAlignment.CENTER,
                    children=[
                        TextButton(
                            key=Key(f"editor_cancel_btn_{turn.id}"),
                            onPressed=on_cancel,
                            onPressedName=f"cancel_edit_{turn.id}",
                            tooltip="Discard edits and close the editor",
                            child=Text(
                                "Cancel",
                                style=TextStyle(
                                    fontSize=13,
                                    color=StudioColors.text_secondary,
                                ),
                            ),
                        ),
                        SizedBox(width=8, key=Key(f"editor_spc_3_{turn.id}")),
                        ElevatedButton(
                            key=Key(f"editor_save_btn_{turn.id}"),
                            onPressed=lambda: on_save(text_ctrl.text, selected_speaker_id),
                            onPressedName=f"save_edit_{turn.id}",
                            tooltip="Save the dialogue text and speaker",
                            style=ButtonStyle(
                                backgroundColor=StudioColors.primary,
                                foregroundColor=StudioColors.text_primary,
                                padding=EdgeInsets.symmetric(horizontal=16, vertical=8),
                                shape=BorderRadius.circular(6),
                            ),
                            child=Row(
                                key=Key(f"editor_save_content_{turn.id}"),
                                crossAxisAlignment=CrossAxisAlignment.CENTER,
                                children=[
                                    Icon(Icons.check_rounded, size=16, color=StudioColors.text_primary),
                                    SizedBox(width=4, key=Key(f"save_spc_{turn.id}")),
                                    Text(
                                        "Save Turn",
                                        style=TextStyle(fontSize=13, fontWeight="bold"),
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            ],
        ),
    )
