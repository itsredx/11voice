"""Speechify voice catalog converted to the UI's shared voice model."""
from typing import List, Optional
from ..elevenlabs.voices import VoiceInfo
from .client import SpeechifyClient


class SpeechifyVoiceManager:
    def __init__(self, client: Optional[SpeechifyClient] = None):
        self.client = client or SpeechifyClient()
        self._cache: List[VoiceInfo] = []

    def fetch_voices(self, force_refresh: bool = False) -> List[VoiceInfo]:
        if self._cache and not force_refresh:
            return list(self._cache)
        parsed = []
        for voice in self.client.get_voices():
            voice_id = voice.get("id", "")
            if not voice_id:
                continue
            gender = voice.get("gender", "unknown")
            parsed.append(VoiceInfo(
                voice_id=voice_id,
                name=voice.get("display_name") or voice_id,
                category=voice.get("type") or "shared",
                preview_url=voice.get("preview_audio"),
                labels={"gender": gender, "accent": voice.get("locale", "")},
                description=", ".join(voice.get("tags", []) or []),
            ))
        self._cache = parsed
        return list(parsed)
