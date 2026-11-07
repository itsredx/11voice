# ── Imports & Layout ───────────────────────────────────────────────────
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
    Colors,
    Container,
    Icon,
    IconButton,
    Icons,
    Row,
    Text,
)
from ..constants.colors import StudioColors


# ── Studio Header Bar Component ────────────────────────────────────────
def build_heading(title: str = "11Voice Conversation Studio", on_refresh_devices=None):
    """Top application header with studio branding and device refresh action."""
    return Container(
        key=Key("studio_heading_container"),
        padding=EdgeInsets.symmetric(horizontal=24, vertical=16),
        color=StudioColors.surface,
        width="-webkit-fill-available",
        child=Row(
            key=Key("heading_row"),
            mainAxisAlignment=MainAxisAlignment.SPACE_BETWEEN,
            crossAxisAlignment=CrossAxisAlignment.CENTER,
            children=[
                # ── Title and Branding ────────────────────────────────
                Row(
                    key=Key("title_group"),
                    crossAxisAlignment=CrossAxisAlignment.CENTER,
                    children=[
                        Icon(
                            Icons.record_voice_over_rounded,
                            key=Key("studio_logo_icon"),
                            size=28,
                            color=StudioColors.primary,
                        ),
                        SizedBox(width=12, key=Key("title_spacer")),
                        Text(
                            title,
                            key=Key("studio_title_text"),
                            style=TextStyle(
                                fontSize=20,
                                fontWeight="bold",
                                color=StudioColors.text_primary,
                            ),
                        ),
                    ],
                ),

                # ── Actions & Device Refresh ──────────────────────────
                Row(
                    key=Key("header_actions_row"),
                    crossAxisAlignment=CrossAxisAlignment.CENTER,
                    mainAxisAlignment=MainAxisAlignment.SPACE_BETWEEN,
                    children=[
                        Text(
                            "PipeWire Multi-Output",
                            key=Key("pipewire_badge"),
                            style=TextStyle(
                                fontSize=12,
                                fontWeight="bold",
                                color=StudioColors.speaker_b,
                            ),
                        ),
                        SizedBox(width=12, key=Key("action_spacer")),
                        IconButton(
                            key=Key("refresh_devices_btn"),
                            icon=Icon(Icons.refresh_rounded, color=StudioColors.text_primary),
                            onPressed=on_refresh_devices,
                            onPressedName="header_refresh_devices",
                            style=ButtonStyle(
                                backgroundColor=StudioColors.surface_elevated,
                                padding=EdgeInsets.all(8),
                                shape=BorderRadius.circular(6),
                            ),
                        ),
                    ],
                ),
            ],
        ),
    )

