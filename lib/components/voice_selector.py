# ── Imports & Setup ──────────────────────────────────────────────────
from typing import Callable, Optional
from pythra.base import Key
from pythra.controllers import DropdownController
from pythra.styles import (
    BorderRadius,
    BorderSide,
    EdgeInsets,
    InputDecoration,
    TextStyle,
)
from pythra import (
    Container,
    Dropdown,
)
from ..constants.colors import StudioColors
from ..elevenlabs.voices import FALLBACK_USABLE_VOICES, VoiceInfo

# ── Preset Voices Catalog ─────────────────────────────────────────────
DEFAULT_VOICES = [
    ("Adam · Male · premade", "pNInz6obpgDQGcFmaJgB"),
    ("Bella · Female · premade", "EXAVITQu4vr4xnSDxMaL"),
]


# ── Voice Selector Component ──────────────────────────────────────────
def build_voice_selector(
    selected_voice_id: Optional[str],
    on_voice_selected: Callable[[str], None],
    widget_key_prefix: str = "voice_sel",
    available_voices: Optional[list[VoiceInfo]] = None,
):
    """
    Dropdown component for selecting ElevenLabs voices for a speaker.
    """
    if available_voices is not None:
        # Seed the selector with the two confirmed usable presets, then add
        # account voices as the remote catalog arrives.
        voices_by_id = {voice.voice_id: voice for voice in FALLBACK_USABLE_VOICES}
        voices_by_id.update(
            {
                voice.voice_id: voice
                for voice in available_voices
                if voice.voice_id and not voice.is_library_voice
            }
        )
        items = [
            (
                f"{voice.name} · {voice.gender.title()} · {voice.category}",
                voice.voice_id,
            )
            for voice in voices_by_id.values()
        ]
    else:
        items = list(DEFAULT_VOICES)
    selected_val = None

    for label, v_id in items:
        if selected_voice_id and v_id == selected_voice_id:
            selected_val = v_id
            break

    if selected_val is None:
        if items:
            selected_val = items[0][1]
        else:
            items = [("No usable voices found", "")]
            selected_val = ""

    controller = DropdownController(selectedValue=selected_val)

    def handle_changed(new_val):
        if new_val:
            on_voice_selected(str(new_val))

    return Container(
        key=Key(f"{widget_key_prefix}_container"),
        child=Dropdown(
            key=Key(f"{widget_key_prefix}_dropdown"),
            controller=controller,
            items=items,
            onChanged=handle_changed,
            hintText="Select Voice",
            decoration=InputDecoration(
                filled=True,
                fillColor=StudioColors.surface_elevated,
                contentPadding=EdgeInsets.symmetric(horizontal=12, vertical=8),
                borderRadius=BorderRadius.circular(6),
                border=BorderSide(color=StudioColors.border, width=1),
                inputStyle=TextStyle(
                    fontSize=12,
                    color=StudioColors.text_primary,
                ),
            ),
        ),
    )

