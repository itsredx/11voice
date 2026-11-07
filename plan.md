Then I'd build this as a **native Linux desktop application**, targeting Arch Linux and Ubuntu.

Given your existing Python experience and Pythra toolkit work, I'd lean towards Python rather than introducing an entirely new stack.

One important architectural decision: **use PipeWire for audio routing, not the system's default audio-device switching.**

That allows us to send two independent audio streams to two different physical devices without repeatedly changing the system audio configuration.

## Proposed stack

| Component | Technology |
|---|---|
| Application | Python |
| GUI | Pythra or PySide6 |
| Voice generation | ElevenLabs API |
| Audio playback | GStreamer |
| Audio routing | PipeWire |
| Audio storage | Local filesystem |
| Configuration | SQLite |
| API communication | httpx |

## 1. How audio routing will work

First, the application discovers available audio devices:

```text
Available outputs:
├── Built-in Audio Analog Stereo
├── Bluetooth Speaker
└── HDMI Audio
```

You assign outputs to speakers:

```python
speaker_a = {
    "name": "Person A",
    "voice_id": "ELEVENLABS_VOICE_A",
    "output_device": "Built-in Audio"
}

speaker_b = {
    "name": "Person B",
    "voice_id": "ELEVENLABS_VOICE_B",
    "output_device": "Bluetooth Speaker"
}
```

The playback engine then selects the appropriate output device for each audio clip.

I'd investigate `python-sounddevice` with PipeWire's compatibility layer for the initial implementation. It gives us explicit output-device selection.

## 2. Conversation playback engine

The most important part is sequencing.

```python
async def play_conversation(turns):
    for turn in turns:
        audio = await generate_or_load_audio(
            text=turn.text,
            voice_id=turn.voice_id
        )

        await play_audio(
            audio=audio,
            output_device=turn.output_device
        )
```

The actual implementation would also handle:
- Device disconnection.
- Bluetooth reconnection.
- Playback errors.
- Audio caching.
- Cancellation and pause.
- Playback completion events.

## 3. Suggested project structure

```text
    refer to Conversation Studio, Pythra project structure
```

## 4. Development roadmap

| Stage | Deliverable | Status |
|---|---|---|
| 1 | Detect audio devices and play audio through individually selected outputs | Completed (PipeWire + GStreamer backend verified) |
| 2 | Integrate ElevenLabs and generate two different voices | Completed (ElevenLabs client, voice manager & synthesis cache) |
| 3 | Build the conversation editor and playback queue | Completed (Sequential PlaybackQueue & ConversationManager) |
| 4 | Add caching, voice management and persistent conversations | Completed (SQLite persistence & AudioCache) |

**My recommendation:** Start with Stage 1 before touching ElevenLabs.

We should first prove that Linux can play one audio clip through the built-in speaker and another through Bluetooth, independently and sequentially. That is the technically interesting part of this project.

Once that works, the rest is relatively straightforward application development.


I'd preserve Pythra's existing architecture rather than introduce a different application structure. The conversation engine, audio backend, ElevenLabs integration and persistence should live inside `lib`, while the GUI remains organized around Pythra screens and components.

Here's the proposed structure.

## Conversation Studio, Pythra project structure

```text
conversation-studio/
├── app_run.log
├── assets/
│   ├── appIcon.png
│   ├── fonts/
│   │   ├── MaterialSymbolsOutlined.ttf
│   │   ├── MaterialSymbolsRounded.ttf
│   │   └── MaterialSymbolsSharp.ttf
│   ├── icons/
│   │   └── icon.ico
│   └── images/
│
├── cmd/
│
├── config.yaml
├── __init__.py
│
├── lib/
│   ├── __init__.py
│   │
│   ├── assets/
│   │   ├── fonts/
│   │   └── icons/
│   │
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── database.py
│   │
│   ├── components/
│   │   ├── __init__.py
│   │   ├── heading.py
│   │   ├── header_actions.py
│   │   ├── speaker_card.py
│   │   ├── conversation_bubble.py
│   │   ├── dialogue_editor.py
│   │   ├── voice_selector.py
│   │   ├── audio_device_selector.py
│   │   ├── playback_controls.py
│   │   └── audio_waveform.py
│   │
│   ├── constants/
│   │   ├── __init__.py
│   │   ├── colors.py
│   │   └── theme.py
│   │
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── dashboard_screen.py
│   │   ├── conversation_screen.py
│   │   ├── speaker_management_screen.py
│   │   ├── voice_library_screen.py
│   │   └── settings_screen.py
│   │
│   ├── state/
│   │   ├── __init__.py
│   │   ├── app_state.py
│   │   ├── conversation_state.py
│   │   ├── playback_state.py
│   │   └── device_state.py
│   │
│   ├── conversation/
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   ├── queue.py
│   │   ├── generator.py
│   │   ├── validator.py
│   │   └── models.py
│   │
│   ├── elevenlabs/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── voices.py
│   │   ├── speech.py
│   │   └── exceptions.py
│   │
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── playback.py
│   │   ├── devices.py
│   │   ├── device_monitor.py
│   │   ├── mixer.py
│   │   ├── formats.py
│   │   └── backends/
│   │       ├── __init__.py
│   │       ├── pipewire.py
│   │       └── base.py
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── audio_cache.py
│   │   ├── conversation_store.py
│   │   └── settings_store.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── file_picker.py
│       ├── shared_preference.py
│       ├── audio_utils.py
│       └── logging.py
│
├── linux/
│   ├── com.pythra.conversation-studio.desktop
│   └── hicolor/
│       ├── 128x128/
│       ├── 256x256/
│       └── 512x512/
│
├── plugins/
│   └── __init__.py
│
├── render/
│   ├── index.html
│   ├── main.js
│   ├── styles.css
│   └── js/
│       ├── pythra_bridge.js
│       └── main.js
│
├── README.md
├── requirements.txt
├── ver.py
└── windows/
    └── appIcon.ico
```

## Important architectural decisions

I would keep these responsibilities separate:

| Module | Responsibility |
|---|---|
| `conversation/` | Dialogue sequencing, speaker turns and conversation management |
| `elevenlabs/` | API communication, voice discovery and speech generation |
| `audio/` | Physical audio devices, playback and routing |
| `storage/` | SQLite persistence and generated audio caching |
| `state/` | Reactive application state |
| `components/` | Reusable Pythra UI components |
| `screens/` | Application pages |

### Three things I particularly recommend

**1. Abstract the audio backend**

Don't couple the application directly to PipeWire.

`audio/backends/base.py` should define an interface, with `pipewire.py` implementing it.

This leaves room for another Linux audio backend later.

**2. Separate voice generation from playback**

ElevenLabs should generate audio files. The audio engine should not know anything about ElevenLabs.

This means you can eventually support other TTS providers without rewriting playback.

**3. Make dialogue editable independently of generated audio**

Each dialogue turn should have its own ID, speaker ID, text and generated audio reference.

When text changes, invalidate only that turn's cached audio.

---

## Suggested data model

I'd start with these entities:

```python
Speaker:
    id
    name
    voice_id
    output_device_id
    volume
    speaking_rate

Conversation:
    id
    title
    created_at
    updated_at

DialogueTurn:
    id
    conversation_id
    speaker_id
    text
    audio_path
    generation_status
    position
```

One important detail: `output_device_id` belongs to the speaker configuration, but it should also be possible to override it on an individual dialogue turn.

That gives you flexibility when experimenting with audio routing.

## Initial development priority

I recommend this order:

1. Audio device discovery through PipeWire.
2. Independent playback routing to built-in and Bluetooth outputs.
3. ElevenLabs voice generation.
4. Conversation and dialogue management.
5. Pythra interface.
6. Persistence and caching.

**One final recommendation:** Don't build the entire interface before validating the audio backend. The dual-output playback is the defining feature of this application, and it deserves an isolated proof of concept first.



