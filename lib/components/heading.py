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
    ElevatedButton,
    Icon,
    Icons,
    Row,
    Text,
)
from ..constants.colors import StudioColors


# ── Studio Header Bar Component ────────────────────────────────────────
def build_heading(
    title: str = "11Voice Conversation Studio",
    on_refresh_devices=None,
    is_syncing_outputs: bool = False,
    active_provider: str = "elevenlabs",
    on_switch_provider=None,
    on_open_settings=None,
):
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
                        ElevatedButton(
                            key=Key("provider_switch_btn"),
                            child=Text(
                                f"Provider: {'ElevenLabs' if active_provider == 'elevenlabs' else 'Speechify'}",
                                key=Key("provider_switch_label"),
                                style=TextStyle(
                                    fontSize=12,
                                    fontWeight="bold",
                                    color=StudioColors.text_primary,
                                ),
                            ),
                            onPressed=on_switch_provider,
                            onPressedName="switch_provider",
                            tooltip="Switch between ElevenLabs and Speechify",
                            style=ButtonStyle(
                                backgroundColor=StudioColors.surface_elevated,
                                padding=EdgeInsets.symmetric(horizontal=12, vertical=8),
                                shape=BorderRadius.circular(6),
                            ),
                        ),
                        SizedBox(width=8, key=Key("provider_btn_spacer")),
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
                        ElevatedButton(
                            key=Key("settings_btn"),
                            child=Text(
                                "Settings",
                                style=TextStyle(
                                    fontSize=12,
                                    fontWeight="bold",
                                    color=StudioColors.text_primary,
                                ),
                            ),
                            onPressed=on_open_settings,
                            onPressedName="open_settings",
                            tooltip="Configure provider API keys",
                            style=ButtonStyle(
                                backgroundColor=StudioColors.surface_elevated,
                                padding=EdgeInsets.symmetric(horizontal=12, vertical=8),
                                shape=BorderRadius.circular(6),
                            ),
                        ),
                        SizedBox(width=8, key=Key("settings_btn_spacer")),
                        ElevatedButton(
                            key=Key("refresh_devices_btn"),
                            child=Row(
                                key=Key("refresh_devices_content"),
                                crossAxisAlignment=CrossAxisAlignment.CENTER,
                                children=[
                                    Icon(Icons.refresh_rounded, color=StudioColors.text_primary),
                                    SizedBox(width=6, key=Key("refresh_devices_gap")),
                                    Text(
                                        "Syncing..." if is_syncing_outputs else "Sync Outputs",
                                        key=Key("refresh_devices_label"),
                                        style=TextStyle(
                                            fontSize=12,
                                            fontWeight="bold",
                                            color=StudioColors.text_primary,
                                        ),
                                    ),
                                ],
                            ),
                            onPressed=on_refresh_devices,
                            onPressedName="header_refresh_devices",
                            tooltip="Refresh the available PipeWire output devices",
                            style=ButtonStyle(
                                backgroundColor=StudioColors.surface_elevated,
                                padding=EdgeInsets.symmetric(horizontal=10, vertical=8),
                                shape=BorderRadius.circular(6),
                            ),
                        ),
                    ],
                ),
            ],
        ),
    )

