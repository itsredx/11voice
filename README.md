# Conversation Studio

**A multi-speaker AI conversation studio for Linux.**

Conversation Studio is a desktop application that lets you create, edit, and play conversations between multiple speakers, each with a distinct AI-generated voice and independently assigned audio output device.

Powered by [ElevenLabs](https://elevenlabs.io/) for voice generation and PipeWire for audio routing, Conversation Studio aims to make multi-speaker audio playback flexible and customizable.

## Features

- **Multi-speaker conversations:** Create conversations with multiple speakers.
- **AI voice generation:** Generate realistic speech using ElevenLabs.
- **Voice customization:** Assign different ElevenLabs voices to individual speakers.
- **Independent audio routing:** Route each speaker to a different physical audio output.
- **Dialogue editor:** Write, edit, reorder, and manage conversation turns.
- **Audio caching:** Reuse generated audio instead of repeatedly calling the TTS API.
- **Playback controls:** Play, pause, resume, and replay conversations.
- **Conversation library:** Select saved scripts or import a conversation JSON file.
- **Device discovery:** Detect available audio output devices.
- **Voice-pair archives:** Keep generated turn audio locally by conversation and speaker voice pairing.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application logic |
| Pythra | Desktop UI framework |
| ElevenLabs API | AI voice generation |
| PipeWire | Linux audio routing |
| SQLite | Local persistence |
| GStreamer | Audio playback |

## How It Works

1. Create a conversation.
2. Add speakers and assign their ElevenLabs voices.
3. Write dialogue for each speaker.
4. Assign an audio output device to each speaker.
5. Generate the speech.
6. Play the conversation with each speaker routed to their assigned output.

Bundled scripts are available from the conversation selector. Imported scripts are saved in
the local SQLite library; their named speakers get separate profiles initialized from the
current Speaker A/B voices. Generated turn audio is cached in `assets/audio_cache/` and copied
to `assets/playback_archive/<conversation-id>/<voice-pair-id>/` so each voice pairing remains
available locally.

To connect ElevenLabs, add your key to the ignored `.env` file as `ELEVENLABS_API_KEY=...`,
then start 11voice with `python3 -m lib.main`. The app loads your account voices on startup.

## Project Status

**Early development.**

The initial development focuses on validating independent audio playback through multiple physical output devices on Linux before implementing the complete application interface.

Features and architecture are subject to change.

## Requirements

- Linux (Arch Linux / Ubuntu)
- Python 3.11+
- PipeWire
- Bluetooth audio support (when using Bluetooth devices)
- ElevenLabs API key

## Installation

Installation instructions will be added as the project matures.

## Configuration

An ElevenLabs API key will be required for speech generation.

Store API credentials locally and never commit them to version control.

## Roadmap

- [X] PipeWire audio device discovery
- [X] Independent audio output routing
- [X] Bluetooth audio support
- [ ] ElevenLabs API integration
- [X] Multi-speaker voice management
- [X] Conversation editor
- [X] Sequential conversation playback
- [X] Audio generation caching
- [ ] SQLite persistence
- [ ] Application packaging and distribution

## Contributing

Contributions, ideas, and suggestions are welcome.

## License

To be determined.
