# ── Imports & Setup ──────────────────────────────────────────────────
from typing import Callable, List, Optional
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
from ..audio.devices import AudioDevice
from ..constants.colors import StudioColors
from .scrollable_dropdown import ScrollableDropdown


# ── Audio Device Selector Component ────────────────────────────────────
def build_audio_device_selector(
    devices: List[AudioDevice],
    selected_device_id: Optional[str],
    on_device_selected: Callable[[str], None],
    widget_key_prefix: str = "dev_sel",
):
    """
    Dropdown component rendering discovered PipeWire output sinks.
    Displays human-friendly sink names with default indicators.
    """
    items = []
    selected_val = None

    for dev in devices:
        default_tag = " [Default]" if dev.is_default else ""
        label = f"{dev.name}{default_tag}"
        items.append((label, dev.id))
        if selected_device_id and dev.id == selected_device_id:
            selected_val = dev.id

    if not items:
        items = [("No PipeWire Sinks Detected", "none")]
        selected_val = "none"
    elif selected_val is None:
        selected_val = items[0][1]

    controller = DropdownController(selectedValue=selected_val)

    def handle_changed(new_val):
        if new_val and new_val != "none":
            on_device_selected(str(new_val))

    return Container(
        key=Key(f"{widget_key_prefix}_container"),
        width="-webkit-fill-available",
        child=ScrollableDropdown(
            key=Key(f"{widget_key_prefix}_dropdown"),
            controller=controller,
            items=items,
            onChanged=handle_changed,
            hintText="Select Output Device",
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

