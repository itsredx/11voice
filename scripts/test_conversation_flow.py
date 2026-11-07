# ── Imports & Setup ──────────────────────────────────────────────────
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.audio import AudioEngine
from lib.backend import Database
from lib.conversation import ConversationManager, Speaker
from lib.storage import AudioCache
from scripts.test_audio_routing import generate_sine_wave


# ── Test Conversation Flow Execution ──────────────────────────────────
def test_conversation_flow():
    print("=" * 70)
    print("  11Voice - Conversation Lifecycle & Dual-Device Playback Test")
    print("=" * 70)

    # 1. Database & Persistence Test
    print("\n[Step 1] Initializing SQLite database...")
    db_path = PROJECT_ROOT / "test_conversations.db"
    if db_path.exists():
        db_path.unlink()
    db = Database(db_path=db_path)

    print("\n[Step 2] Creating Speakers & Device Assignments...")
    audio_engine = AudioEngine()
    devices = audio_engine.get_devices()
    default_dev = audio_engine.get_default_device()
    dev_id = default_dev.id if default_dev else "default_sink"

    speaker_a = Speaker(id="spk_alice", name="Alice", voice_id="voice_alice_01", output_device_id=dev_id)
    speaker_b = Speaker(id="spk_bob", name="Bob", voice_id="voice_bob_02", output_device_id=dev_id)
    db.save_speaker(speaker_a)
    db.save_speaker(speaker_b)

    loaded_speakers = db.get_speakers()
    assert "spk_alice" in loaded_speakers, "Alice should be persisted in DB"
    assert "spk_bob" in loaded_speakers, "Bob should be persisted in DB"
    print("  [+] Speakers successfully saved and retrieved from SQLite.")

    # 2. Audio Cache Test
    print("\n[Step 3] Validating Audio Cache Layer...")
    cache = AudioCache()
    key_alice = cache.derive_cache_key(speaker_a.voice_id, "Hello from Alice!")
    test_audio_a = PROJECT_ROOT / "assets" / "test" / "alice.wav"
    generate_sine_wave(test_audio_a, frequency=523.25, duration=0.8) # C5
    with open(test_audio_a, "rb") as f:
        cache.store(key_alice, f.read(), extension="wav")
    assert cache.exists(key_alice, extension="wav"), "Cache file must exist"
    print("  [+] Cache key derivation and storage validated.")

    # 3. Conversation Manager & Queue Test
    print("\n[Step 4] Building Conversation Dialogue Turns...")
    conv_mgr = ConversationManager(audio_engine=audio_engine, audio_cache=cache)
    conv_mgr.speakers = loaded_speakers
    
    test_audio_b = PROJECT_ROOT / "assets" / "test" / "bob.wav"
    generate_sine_wave(test_audio_b, frequency=659.25, duration=0.8) # E5

    turn_1 = conv_mgr.add_turn(
        speaker_id=speaker_a.id,
        text="Hello from Alice!",
        audio_path=str(test_audio_a),
    )
    turn_2 = conv_mgr.add_turn(
        speaker_id=speaker_b.id,
        text="Hi Alice, Bob here on channel B.",
        audio_path=str(test_audio_b),
    )

    db.save_conversation(conv_mgr.current_conversation)
    loaded_conv = db.get_conversation(conv_mgr.current_conversation.id)
    assert loaded_conv is not None, "Conversation must load from DB"
    assert len(loaded_conv.turns) == 2, "Conversation must contain 2 turns"
    print("  [+] Conversation and dialogue turns successfully persisted.")

    # 4. Sequential Queue Execution
    print("\n[Step 5] Executing Sequential Playback Queue...")
    turns_completed = []

    def on_turn_started(turn, speaker, dev):
        print(f"  >> [Playing] Turn: '{turn.text}' | Speaker: {speaker.name} | Device: {dev.name if dev else 'Default'}")

    def on_turn_completed(turn):
        print(f"  << [Done] Turn '{turn.text}' finished.")
        turns_completed.append(turn.id)

    conv_mgr.queue.on_turn_started = on_turn_started
    conv_mgr.queue.on_turn_completed = on_turn_completed

    conv_mgr.play_conversation()

    # Wait for queue completion
    timeout = 10.0
    start = time.time()
    while conv_mgr.queue.is_playing:
        time.sleep(0.1)
        if time.time() - start > timeout:
            print("  [-] Queue playback timed out!")
            break

    print("\n" + "=" * 70)
    if len(turns_completed) == 2:
        print("  SUCCESS: Full conversation playback flow completed seamlessly!")
    else:
        print("  PARTIAL: Review turns completed:", turns_completed)
    print("=" * 70)

    # Cleanup test db
    if db_path.exists():
        db_path.unlink()


if __name__ == "__main__":
    test_conversation_flow()

