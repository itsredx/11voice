# ── Imports & Data Types ───────────────────────────────────────────────
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ── Generation Status Enum ────────────────────────────────────────────
class GenerationStatus(Enum):
    PENDING = auto()
    GENERATING = auto()
    READY = auto()
    FAILED = auto()


# ── Speaker Model ─────────────────────────────────────────────────────
@dataclass
class Speaker:
    """Represents a speaker with an assigned voice and physical audio output."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "New Speaker"
    voice_id: str = ""                    # ElevenLabs voice identifier
    output_device_id: Optional[str] = None # PipeWire sink node.name
    volume: float = 1.0                   # Range: 0.0 to 1.0
    speaking_rate: float = 1.0            # Range: 0.5 to 2.0


# ── Dialogue Turn Model ────────────────────────────────────────────────
@dataclass
class DialogueTurn:
    """Represents an individual utterance in a conversation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    conversation_id: str = ""
    speaker_id: str = ""
    text: str = ""
    audio_path: Optional[str] = None
    generation_status: GenerationStatus = GenerationStatus.PENDING
    position: int = 0
    output_device_override: Optional[str] = None  # Optional turn-specific device override


# ── Conversation Model ─────────────────────────────────────────────────
@dataclass
class Conversation:
    """Represents a complete dialogue session containing multiple turns."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = "Untitled Conversation"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    turns: list[DialogueTurn] = field(default_factory=list)

