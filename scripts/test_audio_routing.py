# ── Imports & Setup ──────────────────────────────────────────────────
import math
import os
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.audio import AudioEngine, AudioDevice, PlaybackStatus


# ── Synthetic Audio Tone Generator ─────────────────────────────────────
def generate_sine_wave(file_path: Path, frequency: float = 440.0, duration: float = 1.5, sample_rate: int = 44100):
    """Generate a clean uncompressed PCM WAV sine tone without third-party dependencies."""
    num_samples = int(duration * sample_rate)
    amplitude = 16000  # ~50% max int16 volume

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        frames = bytearray()
        for i in range(num_samples):
            val = int(amplitude * math.sin(2 * math.pi * frequency * (i / sample_rate)))
            frames.extend(struct.pack("<h", val))
        wav_file.writeframes(frames)
    print(f"  [+] Generated audio tone: {file_path.name} ({frequency}Hz, {duration}s)")


# ── Virtual Sink Helper for Multi-Output Simulation ───────────────────
def ensure_secondary_sink_for_testing() -> tuple[Optional[int], Optional[str]]:
    """
    If only one physical sink exists, create a temporary PipeWire null sink
    to test independent dual routing without altering the physical setup.
    """
    sink_name = "Virtual_Speaker_B"
    try:
        res = subprocess.run(
            [
                "pactl",
                "load-module",
                "module-null-sink",
                f"sink_name={sink_name}",
                'sink_properties=device.description="Virtual_Speaker_B_(PipeWire_Test)"',
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        module_id = int(res.stdout.strip())
        print(f"  [+] Created virtual secondary test sink '{sink_name}' (Module ID: {module_id})")
        return module_id, sink_name
    except Exception as e:
        print(f"  [!] Note: Could not create virtual sink: {e}")
        return None, None


def remove_secondary_sink(module_id: Optional[int]):
    """Unload the temporary PipeWire null sink."""
    if module_id is not None:
        try:
            subprocess.run(["pactl", "unload-module", str(module_id)], check=True)
            print(f"  [+] Removed temporary virtual sink (Module ID: {module_id})")
        except Exception as e:
            print(f"  [!] Note: Could not unload module: {e}")


# ── Main Test Routine ──────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("  11Voice - Stage 1 Audio Routing & Device Discovery Spike")
    print("=" * 70)

    # 1. Initialize Engine
    print("\n[Step 1] Initializing PipeWire GStreamer AudioEngine...")
    engine = AudioEngine()

    # 2. Discover Devices
    devices = engine.get_devices()
    print(f"\n[Step 2] Discovered {len(devices)} PipeWire Audio Sink(s):")
    for idx, dev in enumerate(devices):
        default_tag = " (DEFAULT)" if dev.is_default else ""
        print(f"   {idx+1}. Node ID: {dev.node_id} | Name: {dev.name}{default_tag}")
        print(f"      Target: {dev.id}")

    if not devices:
        print("[-] ERROR: No audio sinks detected on PipeWire!")
        sys.exit(1)

    # 3. Ensure at least two targets are available for dual-routing verification
    temp_module_id = None
    if len(devices) < 2:
        print("\n[Notice] Single sink found. Creating temporary secondary sink for dual-routing test...")
        temp_module_id, virtual_sink_name = ensure_secondary_sink_for_testing()
        # Give PipeWire a moment to register node
        time.sleep(0.5)
        devices = engine.refresh_devices()
        print(f"  Total sinks now: {len(devices)}")

    # 4. Generate test audio files in assets/test/
    test_dir = PROJECT_ROOT / "assets" / "test"
    tone_a = test_dir / "tone_speaker_a.wav"
    tone_b = test_dir / "tone_speaker_b.wav"
    print("\n[Step 3] Generating synthetic audio samples...")
    generate_sine_wave(tone_a, frequency=440.0, duration=1.2)  # Low A4
    generate_sine_wave(tone_b, frequency=880.0, duration=1.2)  # High A5

    # Select target sinks
    target_1 = devices[0]
    target_2 = devices[1] if len(devices) > 1 else devices[0]

    print("\n[Step 4] Testing Independent Routing:")
    print(f"  -> Turn 1: Speaker A routed to '{target_1.name}' ({target_1.id})")
    print(f"  -> Turn 2: Speaker B routed to '{target_2.name}' ({target_2.id})")

    try:
        # Play Turn 1
        print("\n  >> Playing Turn 1 (Speaker A)...")
        handle_1 = engine.play(str(tone_a), device_id=target_1.id)
        
        # Wait for Turn 1 to finish
        timeout = 5.0
        start = time.time()
        while handle_1.status not in (PlaybackStatus.COMPLETED, PlaybackStatus.ERROR):
            time.sleep(0.1)
            if time.time() - start > timeout:
                print("  [-] Turn 1 timed out!")
                break
        print(f"  << Turn 1 status: {handle_1.status.name}")

        # Play Turn 2
        print("\n  >> Playing Turn 2 (Speaker B)...")
        handle_2 = engine.play(str(tone_b), device_id=target_2.id)
        
        # Wait for Turn 2 to finish
        start = time.time()
        while handle_2.status not in (PlaybackStatus.COMPLETED, PlaybackStatus.ERROR):
            time.sleep(0.1)
            if time.time() - start > timeout:
                print("  [-] Turn 2 timed out!")
                break
        print(f"  << Turn 2 status: {handle_2.status.name}")

        print("\n" + "=" * 70)
        if handle_1.status == PlaybackStatus.COMPLETED and handle_2.status == PlaybackStatus.COMPLETED:
            print("  SUCCESS: Both audio streams routed and completed independently!")
        else:
            print("  PARTIAL/FAILED: Review output statuses above.")
        print("=" * 70)

    finally:
        # Cleanup temporary sink if created
        if temp_module_id is not None:
            print("\n[Cleanup] Cleaning up temporary test sink...")
            remove_secondary_sink(temp_module_id)


if __name__ == "__main__":
    from typing import Optional
    main()

