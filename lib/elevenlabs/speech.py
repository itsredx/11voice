# ── Imports & Setup ──────────────────────────────────────────────────
import logging
from pathlib import Path
from typing import Optional
from ..storage.audio_cache import AudioCache
from ..utils.audio_utils import generate_synthetic_audio_bytes
from .client import ElevenLabsClient
from ..speechify import SpeechifyClient

logger = logging.getLogger(__name__)


# ── Speech Generator Service ──────────────────────────────────────────
class SpeechGenerator:
    """
    Coordinates text-to-speech generation using ElevenLabs with disk caching
    and graceful offline mock fallback for local testing.
    """

    def __init__(
        self,
        client: Optional[ElevenLabsClient] = None,
        cache: Optional[AudioCache] = None,
        mock_mode: bool = False,
    ):
        self.client = client or ElevenLabsClient()
        self.speechify_client = SpeechifyClient()
        self.cache = cache or AudioCache()
        self.mock_mode = mock_mode
        self.provider = "elevenlabs"

    @property
    def model_id(self) -> str:
        return "simba-3.5" if self.provider == "speechify" else "eleven_multilingual_v2"

    def set_provider(self, provider: str) -> None:
        if provider not in {"elevenlabs", "speechify"}:
            raise ValueError(f"Unknown speech provider: {provider}")
        self.provider = provider

    def is_cached(
        self,
        text: str,
        voice_id: str,
        model_id: Optional[str] = None,
        speaking_rate: float = 1.0,
    ) -> bool:
        """Check if audio exists for the given synthesis parameters."""
        key = self.cache.derive_cache_key(
            voice_id=voice_id,
            text=text,
            model_id=model_id or self.model_id,
            speaking_rate=speaking_rate,
            provider="mock" if self.mock_mode else self.provider,
        )
        return self.cache.exists(key, extension="mp3") or self.cache.exists(key, extension="wav")

    def get_cached_path(
        self,
        text: str,
        voice_id: str,
        model_id: Optional[str] = None,
        speaking_rate: float = 1.0,
    ) -> Optional[Path]:
        """Return the Path to cached audio if present."""
        key = self.cache.derive_cache_key(
            voice_id=voice_id,
            text=text,
            model_id=model_id or self.model_id,
            speaking_rate=speaking_rate,
            provider="mock" if self.mock_mode else self.provider,
        )
        if self.cache.exists(key, extension="mp3"):
            return self.cache.get_path(key, extension="mp3")
        if self.cache.exists(key, extension="wav"):
            return self.cache.get_path(key, extension="wav")
        return None

    def generate(
        self,
        text: str,
        voice_id: str,
        model_id: Optional[str] = None,
        speaking_rate: float = 1.0,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        force_regenerate: bool = False,
    ) -> Path:
        """
        Generate audio for dialogue text. Returns Path to local audio file.
        Uses cached version if already generated.
        """
        model_id = model_id or self.model_id
        cache_key = self.cache.derive_cache_key(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            speaking_rate=speaking_rate,
            provider="mock" if self.mock_mode else self.provider,
        )

        if not force_regenerate:
            cached = self.get_cached_path(text, voice_id, model_id, speaking_rate)
            if cached:
                logger.info("Cache hit for voice '%s': %s", voice_id, cached.name)
                return cached

        # Synthetic output is opt-in only; missing credentials must not look like a
        # successful ElevenLabs generation to the user.
        if self.mock_mode:
            logger.info("Generating synthetic mock audio for '%s'...", voice_id)
            # Vary pitch based on hash of voice_id for distinctive speaker tones
            pitch = 380.0 + (hash(voice_id) % 240)
            audio_bytes = generate_synthetic_audio_bytes(text=text, frequency=pitch)
            return self.cache.store(cache_key, audio_bytes, extension="wav")

        if self.provider == "speechify":
            logger.info("Requesting synthesis from Speechify for '%s'...", voice_id)
            audio_bytes = self.speechify_client.generate_tts_bytes(
                text=text, voice_id=voice_id, speed=speaking_rate,
            )
        else:
            logger.info("Requesting synthesis from ElevenLabs for '%s'...", voice_id)
            audio_bytes = self.client.generate_tts_bytes(
                text=text,
                voice_id=voice_id,
                model_id=model_id,
                stability=stability,
                similarity_boost=similarity_boost,
                speed=speaking_rate,
            )
        return self.cache.store(cache_key, audio_bytes, extension="mp3")
