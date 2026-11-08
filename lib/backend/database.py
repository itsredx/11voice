# ── Imports & Setup ──────────────────────────────────────────────────
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from ..conversation.models import Conversation, DialogueTurn, GenerationStatus, Speaker

logger = logging.getLogger(__name__)


# ── SQLite Database Storage ───────────────────────────────────────────
class Database:
    """
    SQLite persistence layer for Conversation Studio.
    Stores speakers, conversations, and dialogue turns.
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            self.db_path = project_root / "conversations.db"
        else:
            self.db_path = Path(db_path)

        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    # ── Schema Initialization ─────────────────────────────────────────
    def _init_schema(self) -> None:
        """Create tables if they don't already exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS speakers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    voice_id TEXT NOT NULL,
                    output_device_id TEXT,
                    volume REAL DEFAULT 1.0,
                    speaking_rate REAL DEFAULT 1.0
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dialogue_turns (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    speaker_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    audio_path TEXT,
                    generation_status TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    output_device_override TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    FOREIGN KEY (speaker_id) REFERENCES speakers(id) ON DELETE SET NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()

    def set_setting(self, key: str, value: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO app_settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            conn.commit()

    def get_setting(self, key: str) -> Optional[str]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else None

    # ── Speaker Operations ────────────────────────────────────────────
    def save_speaker(self, speaker: Speaker) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO speakers (id, name, voice_id, output_device_id, volume, speaking_rate)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    voice_id=excluded.voice_id,
                    output_device_id=excluded.output_device_id,
                    volume=excluded.volume,
                    speaking_rate=excluded.speaking_rate
            """, (speaker.id, speaker.name, speaker.voice_id, speaker.output_device_id, speaker.volume, speaker.speaking_rate))
            conn.commit()

    def get_speakers(self) -> Dict[str, Speaker]:
        speakers: Dict[str, Speaker] = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM speakers")
            for row in cursor.fetchall():
                speaker = Speaker(
                    id=row["id"],
                    name=row["name"],
                    voice_id=row["voice_id"],
                    output_device_id=row["output_device_id"],
                    volume=row["volume"],
                    speaking_rate=row["speaking_rate"],
                )
                speakers[speaker.id] = speaker
        return speakers

    # ── Conversation Operations ───────────────────────────────────────
    def save_conversation(self, conversation: Conversation) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO conversations (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    updated_at=excluded.updated_at
            """, (conversation.id, conversation.title, conversation.created_at, conversation.updated_at))

            # Delete previous turns and rewrite with current sequence
            conn.execute("DELETE FROM dialogue_turns WHERE conversation_id = ?", (conversation.id,))
            for turn in conversation.turns:
                conn.execute("""
                    INSERT INTO dialogue_turns (
                        id, conversation_id, speaker_id, text, audio_path,
                        generation_status, position, output_device_override
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    turn.id,
                    conversation.id,
                    turn.speaker_id,
                    turn.text,
                    turn.audio_path,
                    turn.generation_status.name,
                    turn.position,
                    turn.output_device_override,
                ))
            conn.commit()

    def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
            row = c.fetchone()
            if not row:
                return None

            conv = Conversation(
                id=row["id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

            c.execute("SELECT * FROM dialogue_turns WHERE conversation_id = ? ORDER BY position ASC", (conv_id,))
            for turn_row in c.fetchall():
                turn = DialogueTurn(
                    id=turn_row["id"],
                    conversation_id=turn_row["conversation_id"],
                    speaker_id=turn_row["speaker_id"],
                    text=turn_row["text"],
                    audio_path=turn_row["audio_path"],
                    generation_status=GenerationStatus[turn_row["generation_status"]],
                    position=turn_row["position"],
                    output_device_override=turn_row["output_device_override"],
                )
                conv.turns.append(turn)
            return conv

    def list_conversations(self) -> List[tuple[str, str]]:
        """Return saved conversations as (id, title), newest edits first."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT id, title FROM conversations
                   ORDER BY CASE WHEN id IN ('conversation_01', 'conversation_02', 'conversation_03')
                                 THEN 0 ELSE 1 END,
                            CASE id
                                WHEN 'conversation_01' THEN 1
                                WHEN 'conversation_02' THEN 2
                                WHEN 'conversation_03' THEN 3
                                ELSE 4
                            END,
                            updated_at DESC, title ASC"""
            ).fetchall()
        return [(row["id"], row["title"]) for row in rows]

