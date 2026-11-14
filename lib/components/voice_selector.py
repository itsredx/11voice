# ── Imports & Setup ──────────────────────────────────────────────────
from typing import Callable, Optional
from pythra.base import Key
from pythra.controllers import DropdownController
from pythra.styles import (
    BorderRadius,
    BorderSide,
    DropdownTheme,
    EdgeInsets,
    InputDecoration,
    TextStyle,
)
from pythra import (
    Colors,
    Container,
)
from ..constants.colors import StudioColors
from ..elevenlabs.voices import FALLBACK_USABLE_VOICES, VoiceInfo
from .scrollable_dropdown import ScrollableDropdown

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
    provider: str = "elevenlabs",
):
    """
    Dropdown component for selecting ElevenLabs voices for a speaker.
    """
    if available_voices is not None:
        # Seed the selector with confirmed ElevenLabs presets while its
        # remote catalog loads. Speechify voices must come from its own catalog.
        voices_by_id = (
            {voice.voice_id: voice for voice in FALLBACK_USABLE_VOICES}
            if provider == "elevenlabs" else {}
        )
        voices_by_id.update(
            {
                voice.voice_id: voice
                for voice in available_voices
                if voice.voice_id and (provider != "elevenlabs" or not voice.is_library_voice)
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
    # Pythra's dropdown keeps its JS options from the initial widget mount.
    # Give it a new key when the async catalog changes so reconciliation
    # remounts the dropdown with the newly fetched options.
    catalog_version = hash((provider, tuple(value for _, value in items)))
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
        width="-webkit-fill-available",
        child=ScrollableDropdown(
            key=Key(f"{widget_key_prefix}_dropdown_{catalog_version}"),
            controller=controller,
            items=items,
            onChanged=handle_changed,
            hintText="Select Voice",
            theme=DropdownTheme(
                dropdownColor=Colors.hex("#F8FAFC"),
                dropdownTextColor=Colors.hex("#0F172A"),
                dropdownHoverColor=Colors.hex("#F8FAFC"),
                itemHoverColor=Colors.hex("#C7D2FE"),
                selectedItemColor=Colors.hex("#E0E7FF"),
            ),
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

