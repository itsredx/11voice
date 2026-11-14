# ── Imports & Layout ───────────────────────────────────────────────────
from typing import Callable, Optional
from pythra.base import Key
from pythra.styles import (
    BorderRadius,
    BorderSide,
    BoxDecoration,
    ButtonStyle,
    CrossAxisAlignment,
    EdgeInsets,
    MainAxisAlignment,
    TextStyle,
    Colors,
)
from pythra.widgets import SizedBox
from pythra import (
    Column,
    Container,
    Icon,
    IconButton,
    Icons,
    Row,
    Text,
)
from ..constants.colors import StudioColors
from ..conversation.models import DialogueTurn, Speaker


# ── Dialogue Turn Bubble Component ─────────────────────────────────────
def build_conversation_bubble(
    turn: DialogueTurn,
    speaker: Speaker,
    is_active: bool = False,
    is_cached: bool = False,
    is_generating: bool = False,
    device_label: str = "Default Sink",
    accent_color=StudioColors.speaker_a,
    on_preview: Optional[Callable[[], None]] = None,
    on_generate: Optional[Callable[[], None]] = None,
    on_edit: Optional[Callable[[], None]] = None,
    on_delete: Optional[Callable[[], None]] = None,
):
    """
    Renders an individual turn bubble in the conversation timeline with
    cache status pill, single-turn playback preview, re-generate action,
    speaker badge, and routing target.
    """
    bg_color = StudioColors.active_turn_bg if is_active else StudioColors.surface

    # Status tag color & label
    if is_generating:
        status_color = StudioColors.primary
        status_label = "Synthesizing..."
    elif is_cached:
        status_color = StudioColors.success
        status_label = "Ready"
    else:
        status_color = StudioColors.warning
        status_label = "Uncached"

    # Action items list
    action_items = []
    if is_active:
        action_items.extend(
            [
                Icon(
                    Icons.volume_up_rounded,
                    key=Key(f"play_icon_{turn.id}"),
                    size=16,
                    color=StudioColors.warning,
                ),
                SizedBox(width=4, key=Key(f"play_spc_{turn.id}")),
                Text(
                    "PLAYING",
                    key=Key(f"play_txt_{turn.id}"),
                    style=TextStyle(
                        fontSize=11,
                        fontWeight="bold",
                        color=StudioColors.warning,
                    ),
                ),
                SizedBox(width=30, key=Key(f"play_spc2_{turn.id}")),
            ]
        )

    # Single-turn preview button
    action_items.append(
        IconButton(
            key=Key(f"turn_preview_btn_{turn.id}"),
            icon=Icon(
                Icons.play_circle_rounded,
                size=18,
                color=StudioColors.speaker_b,
            ),
            onPressed=on_preview,
            onPressedName=f"preview_turn_{turn.id}",
            style=ButtonStyle(
                padding=EdgeInsets.all(4),
                shape=BorderRadius.circular(4),
                backgroundColor=Colors.hex("#0f172a")
            ),
        )
    )
    action_items.append(SizedBox(width=4, key=Key(f"preview_spc_{turn.id}")))

    # Single-turn generate / re-synthesize audio button
    action_items.append(
        IconButton(
            key=Key(f"turn_gen_btn_{turn.id}"),
            icon=Icon(
                Icons.auto_awesome_rounded,
                size=16,
                color=StudioColors.primary,
            ),
            onPressed=on_generate,
            onPressedName=f"generate_turn_{turn.id}",
            style=ButtonStyle(
                padding=EdgeInsets.all(4),
                shape=BorderRadius.circular(4),
                backgroundColor=Colors.hex("#0f172a")
            ),
        )
    )
    action_items.append(SizedBox(width=4, key=Key(f"gen_spc_{turn.id}")))

    # Edit button
    action_items.append(
        IconButton(
            key=Key(f"turn_edit_btn_{turn.id}"),
            icon=Icon(
                Icons.edit_note_rounded,
                size=18,
                color=StudioColors.text_secondary,
            ),
            onPressed=on_edit,
            onPressedName=f"edit_turn_{turn.id}",
            style=ButtonStyle(
                padding=EdgeInsets.all(4),
                shape=BorderRadius.circular(4),
                backgroundColor=Colors.hex("#0f172a")
            ),
        )
    )
    action_items.append(SizedBox(width=4, key=Key(f"action_spc_{turn.id}")))

    # Delete button
    action_items.append(
        IconButton(
            key=Key(f"turn_delete_btn_{turn.id}"),
            icon=Icon(
                Icons.delete_outline_rounded,
                size=18,
                color=StudioColors.text_muted,
            ),
            onPressed=on_delete,
            onPressedName=f"delete_turn_{turn.id}",
            style=ButtonStyle(
                padding=EdgeInsets.all(4),
                shape=BorderRadius.circular(4),
                backgroundColor=Colors.hex("#0f172a")
            ),
        )
    )

    bubble_decoration = BoxDecoration(
        color=bg_color,
        borderRadius=BorderRadius.circular(10),
        border=(
            BorderSide(color=StudioColors.active_turn_border, width=1)
            if is_active
            else None
        ),
    )

    return Container(
        key=Key(f"turn_bubble_{turn.id}"),
        padding=EdgeInsets.all(16),
        decoration=bubble_decoration,
        height="-webkit-fill-available",
        child=Column(
            key=Key(f"turn_col_{turn.id}"),
            crossAxisAlignment=CrossAxisAlignment.START,
            children=[
                # ── Speaker & Status Header ───────────────────────────
                Row(
                    key=Key(f"turn_hdr_{turn.id}"),
                    mainAxisAlignment=MainAxisAlignment.SPACE_BETWEEN,
                    crossAxisAlignment=CrossAxisAlignment.CENTER,
                    children=[
                        Row(
                            key=Key(f"turn_speaker_grp_{turn.id}"),
                            crossAxisAlignment=CrossAxisAlignment.CENTER,
                            children=[
                                Container(
                                    key=Key(f"turn_dot_{turn.id}"),
                                    width=10,
                                    height=10,
                                    decoration=BoxDecoration(
                                        color=accent_color,
                                        borderRadius=BorderRadius.circular(5),
                                    ),
                                ),
                                SizedBox(width=8, key=Key(f"turn_spc_1_{turn.id}")),
                                Text(
                                    speaker.name,
                                    key=Key(f"turn_speaker_name_{turn.id}"),
                                    style=TextStyle(
                                        fontSize=13,
                                        fontWeight="bold",
                                        color=accent_color,
                                    ),
                                ),
                                SizedBox(width=10, key=Key(f"turn_spc_2_{turn.id}")),
                                Text(
                                    f"-> {device_label}",
                                    key=Key(f"turn_device_lbl_{turn.id}"),
                                    style=TextStyle(
                                        fontSize=11,
                                        color=StudioColors.text_muted,
                                        fontFamily="monospace",
                                    ),
                                ),
                                SizedBox(
                                    width=10, key=Key(f"status_pill_spc_{turn.id}")
                                ),
                                Container(
                                    key=Key(f"turn_status_pill_{turn.id}"),
                                    padding=EdgeInsets.symmetric(
                                        horizontal=6, vertical=2
                                    ),
                                    decoration=BoxDecoration(
                                        color=StudioColors.surface_elevated,
                                        borderRadius=BorderRadius.circular(4),
                                    ),
                                    child=Text(
                                        status_label,
                                        key=Key(f"turn_status_txt_{turn.id}"),
                                        style=TextStyle(
                                            fontSize=10,
                                            fontWeight="bold",
                                            color=status_color,
                                        ),
                                    ),
                                ),
                            ],
                        ),
                        Container(
                            key=Key(f"Turn_Actions_{turn.id}"),
                            # color='red',
                            child=Row(
                                key=Key(f"turn_actions_{turn.id}"),
                                crossAxisAlignment=CrossAxisAlignment.CENTER,
                                children=action_items,
                            ),
                        ),
                    ],
                ),
                SizedBox(height=10, key=Key(f"turn_spc_3_{turn.id}")),
                # ── Dialogue Utterance Text ───────────────────────────
                Container(
                    key=Key(f"turn_text_{turn.id}_cont"),
                    width="-webkit-fill-available",
                    height="-webkit-fill-available",
                    child=Text(
                        turn.text,
                        key=Key(f"turn_text_{turn.id}"),
                        overflow="ellipsis",
                        maxLines=4,
                        style=TextStyle(
                            fontSize=15,
                            color=StudioColors.text_primary,
                            lineHeight=1.4,
                        ),
                    ),
                ),
            ],
        ),
    )
