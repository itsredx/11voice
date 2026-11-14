"""Small HTTP client for the Speechify text-to-speech API."""
import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode


class SpeechifyClient:
    BASE_URL = "https://api.speechify.ai/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("SPEECHIFY_API_KEY", "") or self._read_local_api_key()

    @staticmethod
    def _read_local_api_key() -> str:
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                name, separator, value = line.partition("=")
                if separator and name.strip() == "SPEECHIFY_API_KEY":
                    return value.strip().strip("\"'")
        except OSError:
            pass
        return ""

    def _request(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> bytes:
        if not self.api_key:
            raise RuntimeError("No Speechify API key. Add it in Settings.")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "11Voice-ConversationStudio/1.0",
        }
        payload = None
        if data is not None:
            payload = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.BASE_URL}{endpoint}", data=payload, headers=headers,
            method="POST" if payload is not None else "GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Speechify API error ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error communicating with Speechify: {exc}") from exc

    def get_voices(self) -> List[Dict[str, Any]]:
        voices: List[Dict[str, Any]] = []
        cursor = None
        seen_cursors = set()
        while True:
            params = {"limit": 200}
            if cursor:
                if cursor in seen_cursors:
                    break
                seen_cursors.add(cursor)
                params["cursor"] = cursor
            result = json.loads(self._request(f"/voices?{urlencode(params)}").decode("utf-8"))
            voices.extend(result.get("voices", []))
            cursor = result.get("next_cursor")
            if not result.get("has_more") or not cursor:
                break
        return voices

    def generate_tts_bytes(self, text: str, voice_id: str, speed: float = 1.0) -> bytes:
        # SSML prosody rate preserves the speaking-rate control used by the UI.
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        input_text = escaped
        if abs(speed - 1.0) > 0.01:
            percent = max(70, min(130, round(speed * 100)))
            input_text = f'<speak><prosody rate="{percent}%">{escaped}</prosody></speak>'
        result = json.loads(self._request("/audio/speech", {
            "input": input_text,
            "voice_id": voice_id,
            "model": "simba-3.5",
            "audio_format": "mp3",
        }).decode("utf-8"))
        return base64.b64decode(result["audio_data"])
