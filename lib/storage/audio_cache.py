# ── Imports & Cache Constants ──────────────────────────────────────────
import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Audio Cache Manager ────────────────────────────────────────────────
class AudioCache:
    """
    Manages cached TTS audio files on the local filesystem.
    Avoids redundant ElevenLabs API calls by hashing synthesis parameters.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            # Default to assets/audio_cache in project root
            project_root = Path(__file__).resolve().parent.parent.parent
            self.cache_dir = project_root / "assets" / "audio_cache"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ── Key Derivation ────────────────────────────────────────────────
    @staticmethod
    def derive_cache_key(
        voice_id: str,
        text: str,
        model_id: str = "eleven_multilingual_v2",
        speaking_rate: float = 1.0,
    ) -> str:
        """Generate a deterministic SHA-256 hash for speech synthesis inputs."""
        normalized_text = text.strip()
        payload = f"{voice_id}|{normalized_text}|{model_id}|{speaking_rate:.2f}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ── Cache Access & Persistence ────────────────────────────────────
    def get_path(self, cache_key: str, extension: str = "mp3") -> Path:
        """Return the target file path for a cache key."""
        return self.cache_dir / f"{cache_key}.{extension}"

    def exists(self, cache_key: str, extension: str = "mp3") -> bool:
        """Check if cached audio exists on disk and is non-empty."""
        path = self.get_path(cache_key, extension)
        return path.exists() and path.stat().st_size > 0

    def store(self, cache_key: str, audio_bytes: bytes, extension: str = "mp3") -> Path:
        """Save generated audio bytes to disk under the specified cache key."""
        target_path = self.get_path(cache_key, extension)
        temp_path = self.cache_dir / f"{cache_key}.tmp"
        
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)
            
        temp_path.replace(target_path)
        logger.info("Cached audio stored: %s (%d bytes)", target_path.name, len(audio_bytes))
        return target_path

    def invalidate(self, cache_key: str, extension: str = "mp3") -> bool:
        """Delete cached audio for a specific cache key."""
        path = self.get_path(cache_key, extension)
        if path.exists():
            try:
                path.unlink()
                logger.info("Invalidated cached audio: %s", path.name)
                return True
            except OSError as e:
                logger.warning("Failed to invalidate cache file %s: %s", path, e)
        return False

    def clear(self) -> int:
        """Remove all cached audio files."""
        count = 0
        for item in self.cache_dir.glob("*.*"):
            if item.is_file():
                try:
                    item.unlink()
                    count += 1
                except OSError:
                    pass
        logger.info("Cleared %d cached audio files.", count)
        return count

