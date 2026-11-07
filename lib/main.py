# ── Imports & Framework Dependencies ───────────────────────────────────
from typing import Union
from pythra.base import Key
from pythra import (
    Framework,
    State,
    StatefulWidget,
    StatelessWidget,
)
from lib.screens.conversation_screen import ConversationScreen


# ── App Initialization Wrapper ─────────────────────────────────────────
def runApp(rootWidget: Union[StatefulWidget, StatelessWidget]):
    """
    Class decorator that initializes PyThra, mounts the root widget,
    and runs the application loop.
    """
    app = Framework.instance()
    app.set_root(rootWidget())
    app.run()
    return rootWidget


# ── Conversation Studio Root App State ─────────────────────────────────
class ConversationStudioAppState(State):
    """Mounts the primary Conversation Studio workspace screen."""

    def build(self):
        return ConversationScreen(key=Key("conversation_studio_screen_root"))


# ── Conversation Studio Root Widget ────────────────────────────────────
@runApp
class ConversationStudioApp(StatefulWidget):
    """The root widget of the 11Voice desktop application."""

    def __init__(self, key=Key("conversation_studio_app")):
        super().__init__(key=key)

    def createState(self):
        return ConversationStudioAppState()
