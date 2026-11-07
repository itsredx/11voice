# ── Imports & Setup ──────────────────────────────────────────────────
import io
import math
import struct
import wave
from pathlib import Path
from typing import List, Union


# ── Synthetic WAV Generator ───────────────────────────────────────────
def generate_synthetic_audio_bytes(
    text: str,
    frequency: float = 440.0,
    sample_rate: int = 44100,
) -> bytes:
    """
    Generate synthetic PCM audio bytes proportional to dialogue text length.
    Provides graceful offline audio generation when ElevenLabs API key is absent.
    """
    # Scale duration with word count: ~0.3s per word, bounded between 0.8s and 4.0s
    word_count = len(text.split())
    duration = max(0.8, min(4.0, word_count * 0.35))
    num_samples = int(duration * sample_rate)
    amplitude = 14000

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit PCM
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for i in range(num_samples):
            # Dual frequency harmonic tone for a richer voice-like chime
            t = i / sample_rate
            val1 = 0.7 * math.sin(2 * math.pi * frequency * t)
            val2 = 0.3 * math.sin(2 * math.pi * (frequency * 1.5) * t)
            sample = int(amplitude * (val1 + val2))
            frames.extend(struct.pack("<h", sample))

        wav_file.writeframes(frames)

    return buffer.getvalue()


# ── Audio Stitching & Concatenation ───────────────────────────────────
def concatenate_wav_files(
    input_paths: List[Union[str, Path]],
    output_path: Union[str, Path],
    silence_gap_seconds: float = 0.4,
) -> Path:
    """
    Concatenate multiple PCM WAV files with silence intervals between speaker turns.
    """
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    valid_paths = [Path(p) for p in input_paths if Path(p).exists() and Path(p).stat().st_size > 0]
    if not valid_paths:
        raise ValueError("No valid audio files provided for concatenation.")

    # Read audio parameters from first file
    with wave.open(str(valid_paths[0]), "rb") as first_wav:
        channels = first_wav.getnchannels()
        sampwidth = first_wav.getsampwidth()
        framerate = first_wav.getframerate()

    silence_frames = bytearray(b"\x00" * int(silence_gap_seconds * framerate * channels * sampwidth))

    with wave.open(str(out_p), "wb") as out_wav:
        out_wav.setnchannels(channels)
        out_wav.setsampwidth(sampwidth)
        out_wav.setframerate(framerate)

        for idx, p in enumerate(valid_paths):
            with wave.open(str(p), "rb") as in_wav:
                out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))
            if idx < len(valid_paths) - 1 and silence_gap_seconds > 0:
                out_wav.writeframes(silence_frames)

    return out_p

