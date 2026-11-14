# ── Imports & Client Setup ─────────────────────────────────────────────
import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from .exceptions import AuthenticationError, ElevenLabsError, PaidPlanRequiredError, RateLimitError, VoiceNotFoundError

logger = logging.getLogger(__name__)


# ── ElevenLabs API Client ──────────────────────────────────────────────
class ElevenLabsClient:
    """Lightweight native ElevenLabs HTTP API client."""

    BASE_URL = "https://api.elevenlabs.io/v1"
    V2_BASE_URL = "https://api.elevenlabs.io/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "") or self._read_local_api_key()

    @staticmethod
    def _read_local_api_key() -> str:
        """Read only ELEVENLABS_API_KEY from the project-local .env file."""
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                name, separator, value = line.partition("=")
                if separator and name.strip() == "ELEVENLABS_API_KEY":
                    return value.strip().strip("\"'")
        except OSError:
            pass
        return ""

    # ── Request Dispatcher ────────────────────────────────────────────
    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> bytes:
        if not self.api_key:
            raise AuthenticationError(
                "No ElevenLabs API key provided. Add ELEVENLABS_API_KEY to the local .env file or launch environment."
            )

        url = endpoint if endpoint.startswith("https://") else f"{self.BASE_URL}{endpoint}"
        req_headers = {
            "xi-api-key": self.api_key,
            "Accept": "application/json",
            "User-Agent": "11Voice-ConversationStudio/1.0",
        }
        if headers:
            req_headers.update(headers)

        payload = None
        if data is not None:
            payload = json.dumps(data).encode("utf-8")
            req_headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=payload, headers=req_headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            status = e.code
            error_body = e.read().decode("utf-8", errors="replace")
            logger.error("ElevenLabs HTTP %d: %s", status, error_body)

            if status in (401, 403):
                raise AuthenticationError(f"Authentication failed ({status}): {error_body}")
            elif status == 429:
                raise RateLimitError(f"Rate limit or quota exceeded ({status}): {error_body}")
            elif status == 402:
                try:
                    detail = json.loads(error_body).get("detail", {})
                except json.JSONDecodeError:
                    detail = {}
                if isinstance(detail, dict) and detail.get("code") == "paid_plan_required":
                    raise PaidPlanRequiredError(
                        "This ElevenLabs Voice Library voice requires a paid plan for API use. "
                        "Choose a voice available to your plan."
                    )
                raise ElevenLabsError(f"ElevenLabs API Error ({status}): {error_body}")
            elif status == 404:
                raise VoiceNotFoundError(f"Requested resource not found ({status}): {error_body}")
            else:
                raise ElevenLabsError(f"ElevenLabs API Error ({status}): {error_body}")
        except urllib.error.URLError as e:
            logger.error("Network error reaching ElevenLabs: %s", e)
            raise ElevenLabsError(f"Network error communicating with ElevenLabs: {e}")

    # ── API Methods ───────────────────────────────────────────────────
    def get_voices(self) -> List[Dict[str, Any]]:
        """Fetch the voices available to this user, including premade voices."""
        raw = self._request("/voices", method="GET")
        data = json.loads(raw.decode("utf-8"))
        return data.get("voices", [])

    def generate_tts_bytes(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        speed: float = 1.0,
    ) -> bytes:
        """
        Generate MP3 audio bytes using text-to-speech.
        """
        endpoint = f"/text-to-speech/{voice_id}"
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "speed": min(1.2, max(0.7, speed)),
            },
        }
        return self._request(
            endpoint,
            method="POST",
            data=payload,
            headers={"Accept": "audio/mpeg"},
        )

