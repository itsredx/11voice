from typing import Callable
from pythra.base import Key
from pythra.controllers import TextEditingController
from pythra.styles import (
    BorderRadius, BorderSide, ButtonStyle, CrossAxisAlignment, EdgeInsets,
    InputDecoration, MainAxisAlignment, TextStyle, BoxDecoration, 
)
from pythra.widgets import SizedBox
from pythra import Column, Container, ElevatedButton, Row, Text, TextField
from ..constants.colors import StudioColors


def _provider_key_card(
    provider: str,
    display_name: str,
    controller: TextEditingController,
    has_key: bool,
    on_save: Callable[[], None],
    on_remove: Callable[[], None],
):
    return Container(
        key=Key(f"{provider}_key_card"),
        padding=EdgeInsets.all(18),
        color=StudioColors.surface,
        width="-webkit-fill-available",
        decoration=BoxDecoration(
            borderRadius=BorderRadius.circular(6),
            border=BorderSide(color=StudioColors.border, width=1),
        ),
        child=Column(
            key=Key(f"{provider}_key_col"),
            crossAxisAlignment=CrossAxisAlignment.START,
            children=[
                Text(display_name, style=TextStyle(fontSize=16, fontWeight="bold", color=StudioColors.text_primary)),
                SizedBox(height=6, key=Key(f"{provider}_key_sp_1")),
                Text(
                    "API key saved" if has_key else "No API key saved",
                    style=TextStyle(fontSize=12, color=StudioColors.text_secondary),
                ),
                SizedBox(height=12, key=Key(f"{provider}_key_sp_2")),
                TextField(
                    key=Key(f"{provider}_key_field"),
                    controller=controller,
                    obscureText=True,
                    decoration=InputDecoration(
                        hintText="Enter API key" if not has_key else "Enter a new key to replace the saved key",
                        filled=True,
                        fillColor=StudioColors.surface_elevated,
                        contentPadding=EdgeInsets.symmetric(horizontal=12, vertical=10),
                        borderRadius=BorderRadius.circular(6),
                        border=BorderSide(color=StudioColors.border, width=1),
                        inputStyle=TextStyle(fontSize=13, color=StudioColors.text_primary),
                    ),
                ),
                SizedBox(height=12, key=Key(f"{provider}_key_sp_3")),
                Row(
                    key=Key(f"{provider}_key_actions"),
                    mainAxisAlignment=MainAxisAlignment.END,
                    children=[
                        ElevatedButton(
                            key=Key(f"{provider}_save_key_btn"),
                            onPressed=on_save,
                            onPressedName=f"save_{provider}_key",
                            style=ButtonStyle(
                                backgroundColor=StudioColors.primary,
                                padding=EdgeInsets.symmetric(horizontal=14, vertical=8),
                                shape=BorderRadius.circular(6),
                            ),
                            child=Text("Save API Key", style=TextStyle(fontSize=12, fontWeight="bold", color=StudioColors.text_primary)),
                        ),
                        SizedBox(width=8, key=Key(f"{provider}_key_sp_4")),
                        ElevatedButton(
                            key=Key(f"{provider}_remove_key_btn"),
                            onPressed=on_remove if has_key else None,
                            onPressedName=f"remove_{provider}_key",
                            style=ButtonStyle(
                                backgroundColor=StudioColors.surface_elevated,
                                padding=EdgeInsets.symmetric(horizontal=14, vertical=8),
                                shape=BorderRadius.circular(6),
                            ),
                            child=Text("Remove", style=TextStyle(fontSize=12, color=StudioColors.text_secondary)),
                        ),
                    ],
                ),
            ],
        ),
    )


def build_provider_settings(
    elevenlabs_controller: TextEditingController,
    speechify_controller: TextEditingController,
    has_elevenlabs_key: bool,
    has_speechify_key: bool,
    on_save_key: Callable[[str, str], None],
    on_remove_key: Callable[[str], None],
    on_back: Callable[[], None],
):
    return Container(
        key=Key("provider_settings_page"),
        padding=EdgeInsets.all(24),
        width="-webkit-fill-available",
        child=Column(
            key=Key("provider_settings_col"),
            crossAxisAlignment=CrossAxisAlignment.START,
            children=[
                Row(
                    key=Key("provider_settings_heading"),
                    mainAxisAlignment=MainAxisAlignment.SPACE_BETWEEN,
                    children=[
                        Text("Provider Settings", style=TextStyle(fontSize=21, fontWeight="bold", color=StudioColors.text_primary)),
                        ElevatedButton(
                            key=Key("provider_settings_back_btn"),
                            onPressed=on_back,
                            onPressedName="close_settings",
                            style=ButtonStyle(
                                backgroundColor=StudioColors.surface_elevated,
                                padding=EdgeInsets.symmetric(horizontal=14, vertical=8),
                                shape=BorderRadius.circular(6),
                            ),
                            child=Text("Back to Studio", style=TextStyle(fontSize=12, color=StudioColors.text_primary)),
                        ),
                    ],
                ),
                SizedBox(height=8, key=Key("provider_settings_sp_1")),
                Text(
                    "Keys are stored locally in the project’s ignored .env file.",
                    style=TextStyle(fontSize=12, color=StudioColors.text_secondary),
                ),
                SizedBox(height=18, key=Key("provider_settings_sp_2")),
                _provider_key_card(
                    "elevenlabs", "ElevenLabs", elevenlabs_controller, has_elevenlabs_key,
                    lambda: on_save_key("elevenlabs", elevenlabs_controller.text),
                    lambda: on_remove_key("elevenlabs"),
                ),
                SizedBox(height=14, key=Key("provider_settings_sp_3")),
                _provider_key_card(
                    "speechify", "Speechify", speechify_controller, has_speechify_key,
                    lambda: on_save_key("speechify", speechify_controller.text),
                    lambda: on_remove_key("speechify"),
                ),
            ],
        ),
    )
