# ── Imports & Setup ──────────────────────────────────────────────────
import logging
from pathlib import Path
from typing import Optional
from ..storage.audio_cache import AudioCache
from ..utils.audio_utils import generate_synthetic_audio_bytes
from .client import ElevenLabsClient

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
        self.cache = cache or AudioCache()
        self.mock_mode = mock_mode

    def is_cached(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2",
        speaking_rate: float = 1.0,
    ) -> bool:
        """Check if audio exists for the given synthesis parameters."""
        key = self.cache.derive_cache_key(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            speaking_rate=speaking_rate,
            provider="mock" if self.mock_mode else "elevenlabs",
        )
        return self.cache.exists(key, extension="mp3") or self.cache.exists(key, extension="wav")

    def get_cached_path(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2",
        speaking_rate: float = 1.0,
    ) -> Optional[Path]:
        """Return the Path to cached audio if present."""
        key = self.cache.derive_cache_key(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            speaking_rate=speaking_rate,
            provider="mock" if self.mock_mode else "elevenlabs",
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
        model_id: str = "eleven_multilingual_v2",
        speaking_rate: float = 1.0,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        force_regenerate: bool = False,
    ) -> Path:
        """
        Generate audio for dialogue text. Returns Path to local audio file.
        Uses cached version if already generated.
        """
        cache_key = self.cache.derive_cache_key(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            speaking_rate=speaking_rate,
            provider="mock" if self.mock_mode else "elevenlabs",
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
