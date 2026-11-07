# ── Exceptions ─────────────────────────────────────────────────────────
class ElevenLabsError(Exception):
    """Base exception for all ElevenLabs operations."""
    pass


class AuthenticationError(ElevenLabsError):
    """Raised when the ElevenLabs API key is missing or invalid."""
    pass


class RateLimitError(ElevenLabsError):
    """Raised when ElevenLabs quota or rate limit is exceeded."""
    pass


class VoiceNotFoundError(ElevenLabsError):
    """Raised when a specified voice ID does not exist."""
    pass

