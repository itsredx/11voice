# ── ElevenLabs Package Initialization ──────────────────────────────────
from .client import ElevenLabsClient
from .exceptions import AuthenticationError, ElevenLabsError, PaidPlanRequiredError, RateLimitError, VoiceNotFoundError
from .speech import SpeechGenerator
from .voices import VoiceInfo, VoiceManager

__all__ = [
    "ElevenLabsClient",
    "ElevenLabsError",
    "AuthenticationError",
    "RateLimitError",
    "PaidPlanRequiredError",
    "VoiceNotFoundError",
    "SpeechGenerator",
    "VoiceInfo",
    "VoiceManager",
]

