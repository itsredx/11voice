# ── Imports & Setup ──────────────────────────────────────────────────
from typing import Callable, Optional
from pythra.base import Key
from pythra.styles import (
    BorderRadius,
    ButtonStyle,
    CrossAxisAlignment,
    EdgeInsets,
    MainAxisAlignment,
    TextStyle,
)
from pythra.widgets import SizedBox
from pythra import (
    Column,
    Container,
    ElevatedButton,
    Icon,
    IconButton,
    Icons,
    Row,
    Text,
)
from ..constants.colors import StudioColors


# ── Playback Controls Component ────────────────────────────────────────
def build_playback_controls(
    is_playing: bool,
    is_paused: bool,
    is_generating: bool = False,
    status_text: str = "Ready",
    on_play: Optional[Callable[[], None]] = None,
    on_pause: Optional[Callable[[], None]] = None,
    on_stop: Optional[Callable[[], None]] = None,
    on_generate_all: Optional[Callable[[], None]] = None,
    on_add_turn: Optional[Callable[[], None]] = None,
):
    """
    Control toolbar housing conversation playback triggers,
    audio pre-generation, status display, and new turn creation actions.
    """
    play_pause_icon = Icons.pause_rounded if (is_playing and not is_paused) else Icons.play_arrow_rounded
    play_pause_action = on_pause if (is_playing and not is_paused) else on_play

    return Container(
        key=Key("playback_controls_container"),
        padding=EdgeInsets.symmetric(horizontal=24, vertical=16),
        width="-webkit-fill-available",
        color=StudioColors.surface,
        child=Row(
            key=Key("playback_controls_row"),
            mainAxisAlignment=MainAxisAlignment.SPACE_BETWEEN,
            crossAxisAlignment=CrossAxisAlignment.CENTER,
            children=[
                # ── Transport Controls ────────────────────────────────
                Row(
                    key=Key("transport_btn_group"),
                    crossAxisAlignment=CrossAxisAlignment.CENTER,
                    children=[
                        # Play / Pause primary button
                        IconButton(
                            key=Key("main_play_pause_btn"),
                            icon=Icon(play_pause_icon, size=24, color=StudioColors.text_primary),
                            onPressed=play_pause_action,
                            onPressedName="main_play_pause",
                            style=ButtonStyle(
                                backgroundColor=StudioColors.primary,
                                padding=EdgeInsets.all(12),
                                shape=BorderRadius.circular(30),
                            ),
                        ),
                        SizedBox(width=12, key=Key("ctrl_spc_1")),

                        # Stop button
                        IconButton(
                            key=Key("main_stop_btn"),
                            icon=Icon(Icons.stop_rounded, size=22, color=StudioColors.text_primary),
                            onPressed=on_stop,
                            onPressedName="main_stop",
                            style=ButtonStyle(
                                backgroundColor=StudioColors.surface_elevated,
                                padding=EdgeInsets.all(12),
                                shape=BorderRadius.circular(30),
                            ),
                        ),
                        SizedBox(width=20, key=Key("ctrl_spc_2")),

                        # Status line
                        Column(
                            key=Key("status_col"),
                            crossAxisAlignment=CrossAxisAlignment.START,
                            children=[
                                Text(
                                    "STATUS",
                                    key=Key("status_caption"),
                                    style=TextStyle(
                                        fontSize=10,
                                        fontWeight="bold",
                                        color=StudioColors.text_muted,
                                    ),
                                ),
                                SizedBox(height=2, key=Key("status_spc")),
                                Text(
                                    status_text,
                                    key=Key("status_val"),
                                    style=TextStyle(
                                        fontSize=13,
                                        fontWeight="bold",
                                        color=StudioColors.text_primary,
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),

                # ── Action Buttons ────────────────────────────────────
                Row(
                    key=Key("action_buttons_group"),
                    crossAxisAlignment=CrossAxisAlignment.CENTER,
                    mainAxisAlignment=MainAxisAlignment.END,
                    children=[
                        # Pre-generate all dialogue audio button
                        ElevatedButton(
                            key=Key("gen_all_btn"),
                            onPressed=on_generate_all,
                            onPressedName="main_gen_all",
                            style=ButtonStyle(
                                backgroundColor=StudioColors.surface_elevated,
                                foregroundColor=StudioColors.primary,
                                padding=EdgeInsets.symmetric(horizontal=14, vertical=12),
                                shape=BorderRadius.circular(8),
                            ),
                            child=Row(
                                key=Key("gen_all_row"),
                                crossAxisAlignment=CrossAxisAlignment.CENTER,
                                children=[
                                    Icon(
                                        Icons.auto_awesome_rounded,
                                        size=18,
                                        color=StudioColors.primary,
                                    ),
                                    SizedBox(width=6, key=Key("gen_all_spc")),
                                    Text(
                                        "Synthesize All" if not is_generating else "Synthesizing...",
                                        key=Key("gen_all_label"),
                                        style=TextStyle(
                                            fontSize=13,
                                            fontWeight="bold",
                                            color=StudioColors.primary,
                                        ),
                                    ),
                                ],
                            ),
                        ),
                        SizedBox(width=12, key=Key("action_grp_spc")),

                        # Add Turn Button
                        ElevatedButton(
                            key=Key("add_turn_btn"),
                            onPressed=on_add_turn,
                            onPressedName="main_add_turn",
                            style=ButtonStyle(
                                backgroundColor=StudioColors.surface_elevated,
                                foregroundColor=StudioColors.text_primary,
                                padding=EdgeInsets.symmetric(horizontal=16, vertical=12),
                                shape=BorderRadius.circular(8),
                            ),
                            child=Row(
                                key=Key("add_turn_child_row"),
                                crossAxisAlignment=CrossAxisAlignment.CENTER,
                                children=[
                                    Icon(Icons.add_rounded, size=18, color=StudioColors.text_primary),
                                    SizedBox(width=6, key=Key("add_spc")),
                                    Text(
                                        "Add Turn",
                                        key=Key("add_turn_label"),
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
