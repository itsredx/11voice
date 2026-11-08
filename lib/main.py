# ── Imports & Framework Dependencies ───────────────────────────────────
from pythra.base import Key
from pythra import Framework
from lib.screens.conversation_screen import ConversationScreen


# ── App Initialization Wrapper ─────────────────────────────────────────
def runApp(rootWidget):
    """
    Class decorator that initializes PyThra, mounts the root widget,
    and runs the application loop.
    """
    app = Framework.instance()
    app.set_root(rootWidget())
    app.run()
    return rootWidget


# ── Conversation Studio Root Widget ────────────────────────────────────
@runApp
class ConversationStudioApp(ConversationScreen):
    """Run the conversation screen directly as the stateful application root."""

    def __init__(self, key=Key("conversation_studio_app")):
        super().__init__(key=key)
