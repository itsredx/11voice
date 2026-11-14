# ── Imports & Setup ──────────────────────────────────────────────────
from typing import Callable, List, Optional
from pythra.base import Key
from pythra.styles import (
    BorderRadius,
    BoxDecoration,
    CrossAxisAlignment,
    EdgeInsets,
    MainAxisAlignment,
    TextStyle,
    BorderSide,
)
from pythra.widgets import SizedBox
from pythra import (
    Column,
    Container,
    Icon,
    Icons,
    Row,
    Text,
)
from ..audio.devices import AudioDevice
from ..constants.colors import StudioColors
from ..conversation.models import Speaker
from ..elevenlabs.voices import VoiceInfo
from .audio_device_selector import build_audio_device_selector
from .voice_selector import build_voice_selector


# ── Speaker Card Component ─────────────────────────────────────────────
def build_speaker_card(
    speaker: Speaker,
    devices: List[AudioDevice],
    accent_color=StudioColors.speaker_a,
    on_device_selected: Optional[Callable[[str], None]] = None,
    on_voice_selected: Optional[Callable[[str], None]] = None,
    available_voices: Optional[List[VoiceInfo]] = None,
    provider: str = "elevenlabs",
):
    """
    Card displaying speaker profile, ElevenLabs voice selector dropdown,
    and the dedicated physical PipeWire output routing dropdown.
    """
    return Container(
        key=Key(f"speaker_card_{speaker.id}"),
        padding=EdgeInsets.all(16),
        width="48vw",
        decoration=BoxDecoration(
            color=StudioColors.surface,
            borderRadius=BorderRadius.circular(10),
            border=BorderSide(color=StudioColors.border, width=1),
        ),
        child=Column(
            key=Key(f"speaker_col_{speaker.id}"),
            crossAxisAlignment=CrossAxisAlignment.START,
            children=[
                # ── Speaker Header ────────────────────────────────────
                Row(
                    key=Key(f"speaker_hdr_row_{speaker.id}"),
                    mainAxisAlignment=MainAxisAlignment.SPACE_BETWEEN,
                    crossAxisAlignment=CrossAxisAlignment.CENTER,
                    children=[
                        Row(
                            key=Key(f"speaker_title_row_{speaker.id}"),
                            crossAxisAlignment=CrossAxisAlignment.CENTER,
                            children=[
                                Icon(
                                    Icons.mic_rounded,
                                    key=Key(f"speaker_mic_icon_{speaker.id}"),
                                    size=18,
                                    color=accent_color,
                                ),
                                SizedBox(width=8, key=Key(f"speaker_spc_1_{speaker.id}")),
                                Text(
                                    speaker.name,
                                    key=Key(f"speaker_name_{speaker.id}"),
                                    style=TextStyle(
                                        fontSize=15,
                                        fontWeight="bold",
                                        color=StudioColors.text_primary,
                                    ),
                                ),
                            ],
                        ),
                        Container(
                            key=Key(f"speaker_pill_{speaker.id}"),
                            padding=EdgeInsets.symmetric(horizontal=8, vertical=3),
                            decoration=BoxDecoration(
                                color=StudioColors.surface_elevated,
                                borderRadius=BorderRadius.circular(12),
                            ),
                            child=Text(
                                "Configured",
                                style=TextStyle(
                                    fontSize=10,
                                    color=accent_color,
                                    fontWeight="bold",
                                ),
                            ),
                        ),
                    ],
                ),
                SizedBox(height=12, key=Key(f"speaker_spc_2_{speaker.id}")),

                # ── Voice Selection Row ───────────────────────────────
                Text(
                    "Voice Model",
                    key=Key(f"voice_lbl_{speaker.id}"),
                    style=TextStyle(
                        fontSize=11,
                        color=StudioColors.text_muted,
                        fontWeight="bold",
                    ),
                ),
                SizedBox(height=4, key=Key(f"spk_spc_v_{speaker.id}")),
                build_voice_selector(
                    selected_voice_id=speaker.voice_id,
                    on_voice_selected=on_voice_selected or (lambda v: None),
                    widget_key_prefix=f"voice_sel_{speaker.id}",
                    available_voices=available_voices,
                    provider=provider,
                ),
                SizedBox(height=10, key=Key(f"spk_spc_mid_{speaker.id}")),

                # ── PipeWire Output Target ────────────────────────────
                Text(
                    "Target PipeWire Output",
                    key=Key(f"sink_lbl_{speaker.id}"),
                    style=TextStyle(
                        fontSize=11,
                        color=StudioColors.text_muted,
                        fontWeight="bold",
                    ),
                ),
                SizedBox(height=4, key=Key(f"spk_spc_s_{speaker.id}")),
                build_audio_device_selector(
                    devices=devices,
                    selected_device_id=speaker.output_device_id,
                    on_device_selected=on_device_selected or (lambda d: None),
                    widget_key_prefix=f"dev_sel_{speaker.id}",
                ),
            ],
        ),
    )
