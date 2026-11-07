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

# ── Preset Voices Catalog ─────────────────────────────────────────────
DEFAULT_VOICES = [
    ("Rachel (Calm & Clear)", "21m00Tcm4TlvDq8ikWAM"),
    ("Domi (Strong & Engaging)", "AZnzlk1XvdvUeBnXmlld"),
    ("Bella (Expressive Narrative)", "EXAVITQu4vr4xnSDxMaL"),
    ("Antoni (Warm & Natural)", "ErXwobaYiN019PkySvjV"),
    ("Josh (Deep & Conversational)", "TxGEqnHWrfWFTfGW9XjX"),
    ("Adam (Professional & Narrative)", "pNInz6obpgDQGcFmaJgB"),
    ("Arnold (Crisp & Articulate)", "VR6AewLTigWG4xSOukaG"),
    ("Sam (Dynamic & Lively)", "yoZ06aMxZJJ28mfd3POQ"),
]


# ── Voice Selector Component ──────────────────────────────────────────
def build_voice_selector(
    selected_voice_id: Optional[str],
    on_voice_selected: Callable[[str], None],
    widget_key_prefix: str = "voice_sel",
):
    """
    Dropdown component for selecting ElevenLabs voices for a speaker.
    """
    items = list(DEFAULT_VOICES)
    selected_val = None

    for label, v_id in items:
        if selected_voice_id and v_id == selected_voice_id:
            selected_val = v_id
            break

    if selected_val is None:
        if selected_voice_id:
            items.insert(0, (f"Custom ({selected_voice_id[:8]}...)", selected_voice_id))
            selected_val = selected_voice_id
        else:
            selected_val = items[0][1]

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

