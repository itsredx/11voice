"""Keep generated dialogue turns in folders organized by voice pairing."""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PlaybackArchive:
    def __init__(self, archive_dir: Optional[Path] = None):
        if archive_dir is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            archive_dir = project_root / "assets" / "playback_archive"
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def voice_pair_id(conversation: Conversation, speakers: Dict[str, Speaker]) -> str:
        ordered_ids = []
        for turn in conversation.turns:
            if turn.speaker_id not in ordered_ids:
                ordered_ids.append(turn.speaker_id)
        voice_signature = "|".join(
            f"{speaker_id}:{speakers[speaker_id].voice_id}:"
            f"{speakers[speaker_id].speaking_rate:.2f}"
            for speaker_id in ordered_ids
            if speaker_id in speakers
        )
        return hashlib.sha256(voice_signature.encode("utf-8")).hexdigest()[:16]

    def archive_turn(
        self,
        conversation: Conversation,
        turn: DialogueTurn,
        speakers: Dict[str, Speaker],
        audio_path: str,
    ) -> Optional[Path]:
        source = Path(audio_path)
        if not source.is_file() or source.stat().st_size == 0:
            return None
        pair_id = self.voice_pair_id(conversation, speakers)
        target_dir = self.archive_dir / conversation.id / pair_id
        suffix = source.suffix or ".audio"
        try:
            audio_digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
            target = target_dir / f"turn_{turn.position + 1:03d}_{turn.speaker_id}_{audio_digest}{suffix}"
            target_dir.mkdir(parents=True, exist_ok=True)
            if source.resolve() != target.resolve():
                shutil.copy2(source, target)
            manifest_path = target_dir / "manifest.json"
            manifest = {}
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    manifest = {}
            manifest.update(
                {
                    "conversation_id": conversation.id,
                    "title": conversation.title,
                    "voice_pair_id": pair_id,
                    "speakers": {
                        sid: {
                            "name": profile.name,
                            "voice_id": profile.voice_id,
                            "speaking_rate": profile.speaking_rate,
                        }
                        for sid, profile in speakers.items()
                        if sid in {item.speaker_id for item in conversation.turns}
                    },
                }
            )
            archived_turns = manifest.setdefault("turns", {})
            versions = archived_turns.setdefault(str(turn.position), [])
            if isinstance(versions, dict):
                versions = [versions]
                archived_turns[str(turn.position)] = versions
            if not any(item.get("audio_sha256", "").startswith(audio_digest) for item in versions):
                versions.append(
                    {
                        "turn_id": turn.id,
                        "speaker_id": turn.speaker_id,
                        "text": turn.text,
                        "audio_file": target.name,
                        "audio_sha256": audio_digest,
                    }
                )
            manifest_path.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return target
        except OSError:
            logger.exception("Could not archive generated playback audio: %s", source)
            return None

    def find_turn(
        self,
        conversation: Conversation,
        turn: DialogueTurn,
        speakers: Dict[str, Speaker],
    ) -> Optional[Path]:
        """Find the latest archived audio matching this turn and voice pairing."""
        pair_id = self.voice_pair_id(conversation, speakers)
        target_dir = self.archive_dir / conversation.id / pair_id
        manifest_path = target_dir / "manifest.json"
        if not manifest_path.is_file():
            return None
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            versions = manifest.get("turns", {}).get(str(turn.position), [])
            if isinstance(versions, dict):
                versions = [versions]
            for version in reversed(versions):
                if version.get("text") != turn.text or version.get("speaker_id") != turn.speaker_id:
                    continue
                audio_path = target_dir / str(version.get("audio_file", ""))
                if audio_path.is_file() and audio_path.stat().st_size > 0:
                    return audio_path
        except (OSError, json.JSONDecodeError, AttributeError, TypeError):
            logger.warning("Could not read playback archive manifest: %s", manifest_path)
        return None
