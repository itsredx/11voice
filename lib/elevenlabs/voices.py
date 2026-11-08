# ── Imports & Models ──────────────────────────────────────────────────
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from .client import ElevenLabsClient


# ── Voice Information Model ───────────────────────────────────────────
@dataclass
class VoiceInfo:
    """Parsed voice metadata from ElevenLabs."""
    voice_id: str
    name: str
    category: str = "premade"
    preview_url: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    available_for_tiers: List[str] = field(default_factory=list)
    free_users_allowed: Optional[bool] = None
    is_library_voice: bool = False

    @property
    def gender(self) -> str:
        return self.labels.get("gender", "unknown")

    @property
    def accent(self) -> str:
        return self.labels.get("accent", "neutral")


# These two preset voices were confirmed usable with this account. Keep them
# available while the remote catalog is still loading or temporarily offline.
FALLBACK_USABLE_VOICES = [
    VoiceInfo(
        voice_id="pNInz6obpgDQGcFmaJgB",
        name="Adam",
        category="premade",
        labels={"gender": "male"},
    ),
    VoiceInfo(
        voice_id="EXAVITQu4vr4xnSDxMaL",
        name="Bella",
        category="premade",
        labels={"gender": "female"},
    ),
]


# ── Voice Manager ─────────────────────────────────────────────────────
class VoiceManager:
    """Manages voice discovery, cataloging and metadata."""

    def __init__(self, client: Optional[ElevenLabsClient] = None):
        self.client = client or ElevenLabsClient()
        self._cache: Dict[str, VoiceInfo] = {}

    def fetch_voices(self, force_refresh: bool = False) -> List[VoiceInfo]:
        """Fetch and cache available ElevenLabs voices."""
        if self._cache and not force_refresh:
            return list(self._cache.values())

        raw_voices = self.client.get_voices()
        parsed: Dict[str, VoiceInfo] = {}
        for item in raw_voices:
            v_id = item.get("voice_id", "")
            category = item.get("category") or "premade"
            info = VoiceInfo(
                voice_id=v_id,
                name=item.get("name", "Unnamed Voice"),
                category=category,
                preview_url=item.get("preview_url"),
                labels=item.get("labels", {}),
                description=item.get("description", "") or "",
                available_for_tiers=item.get("available_for_tiers", []) or [],
                free_users_allowed=(item.get("sharing") or {}).get("free_users_allowed"),
                # `sharing` metadata is also present on some built-in voices,
                # so it does not mean the voice is paywalled. The category is
                # the reliable catalog signal for Voice Library entries.
                is_library_voice=category.lower() in {"professional", "community"},
            )
            parsed[v_id] = info

        self._cache = parsed
        return list(parsed.values())

    def get_voice(self, voice_id: str) -> Optional[VoiceInfo]:
        """Get info for a specific voice ID."""
        if voice_id not in self._cache:
            self.fetch_voices()
        return self._cache.get(voice_id)

