"""Load portable conversation JSON files into the app's data models."""
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Tuple

from .models import Conversation, DialogueTurn, GenerationStatus, Speaker


def load_conversation_json(
    path: Path,
    existing_speakers: Dict[str, Speaker],
    conversation_id: str | None = None,
) -> Tuple[Conversation, Dict[str, Speaker]]:
    """Parse a conversation JSON file and map its speakers onto app speakers.

    Imported dialogue audio is intentionally reset to pending: audio is generated
    for the currently selected voice pairing and stored in the local cache/archive.
    """
    try:
        payload: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read conversation JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Conversation JSON must contain an object at the top level.")

    raw_speakers = payload.get("speakers")
    raw_turns = payload.get("turns")
    if not isinstance(raw_speakers, list) or not raw_speakers:
        raise ValueError("Conversation JSON must include a non-empty speakers list.")
    if not isinstance(raw_turns, list):
        raise ValueError("Conversation JSON must include a turns list.")

    conv_id = conversation_id or str(payload.get("id") or uuid.uuid4().hex[:8])
    preferred_ids = ["spk_a", "spk_b"]
    app_speakers = [existing_speakers[sid] for sid in preferred_ids if sid in existing_speakers]
    app_speakers.extend(
        speaker for sid, speaker in existing_speakers.items() if sid not in preferred_ids
    )
    if len(app_speakers) < len(raw_speakers):
        raise ValueError(
            f"This file has {len(raw_speakers)} speakers, but 11voice has only "
            f"{len(app_speakers)} configured speaker profiles."
        )

    speaker_ids: Dict[str, str] = {}
    imported_speakers: Dict[str, Speaker] = {}
    for index, raw_speaker in enumerate(raw_speakers):
        if not isinstance(raw_speaker, dict) or not raw_speaker.get("id"):
            raise ValueError("Each speaker must be an object with an id.")
        template = app_speakers[index]
        imported_speaker = Speaker(
            id=f"{conv_id}_{uuid.uuid4().hex[:8]}",
            name=str(raw_speaker.get("name") or template.name),
            voice_id=template.voice_id,
            output_device_id=template.output_device_id,
            volume=template.volume,
            speaking_rate=template.speaking_rate,
        )
        speaker_ids[str(raw_speaker["id"])] = imported_speaker.id
        imported_speakers[imported_speaker.id] = imported_speaker

    title = str(payload.get("title") or Path(path).stem)
    now = time.time()
    created_at = payload.get("created_at")
    updated_at = payload.get("updated_at")
    conversation = Conversation(
        id=conv_id,
        title=title,
        created_at=float(created_at) if isinstance(created_at, (int, float)) else now,
        updated_at=float(updated_at) if isinstance(updated_at, (int, float)) else now,
    )

    ordered_turns = sorted(
        raw_turns,
        key=lambda item: item.get("position", 0) if isinstance(item, dict) else 0,
    )
    for position, raw_turn in enumerate(ordered_turns):
        if not isinstance(raw_turn, dict):
            raise ValueError(f"Turn {position + 1} must be an object.")
        source_speaker_id = str(raw_turn.get("speaker_id", ""))
        mapped_speaker_id = speaker_ids.get(source_speaker_id)
        text = raw_turn.get("text")
        if mapped_speaker_id is None:
            raise ValueError(f"Turn {position + 1} references an unknown speaker.")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Turn {position + 1} must contain non-empty text.")
        conversation.turns.append(
            DialogueTurn(
                id=uuid.uuid4().hex[:8],
                conversation_id=conv_id,
                speaker_id=mapped_speaker_id,
                text=text,
                audio_path=None,
                generation_status=GenerationStatus.PENDING,
                position=position,
            )
        )
    if not conversation.turns:
        raise ValueError("Conversation JSON contains no dialogue turns.")
    return conversation, imported_speakers
