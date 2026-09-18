# [Text to Audio](https://pydantic.dev/docs/ai/examples/realtime/realtime-text-to-audio/)

# Text to Audio

The smallest possible [realtime session](https://pydantic.dev/docs/ai/realtime/overview/): send plain text from Python and hear the model speak the reply. Sending text into an OpenAI realtime session asks the model to respond right away, so there's no microphone, voice-activity detection, or manual turn-taking to manage -- just [`send()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.send) and iterate the session's events.

Demonstrates:

-   [realtime sessions](https://pydantic.dev/docs/ai/realtime/overview/)
-   the text-in / audio-out path (no audio hardware required)
-   streaming [`SpeechPartDelta`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPartDelta) audio and transcript deltas

The script streams the spoken reply back, prints the transcript as it arrives, and saves the audio to a `.wav` file you can play afterwards. It's a handy starting point for turning an existing text chatbot into one that talks, or for generating spoken snippets like a voicemail greeting.

## Running the Example

The realtime model runs on `gpt-realtime`, so you'll need an OpenAI API key set via `OPENAI_API_KEY`.

With [dependencies installed and environment variables set](https://pydantic.dev/docs/ai/examples/setup/#usage), run:

-   [pip](#tab-panel-54)
-   [uv](#tab-panel-55)

Terminal

```bash
python -m pydantic_ai_examples.realtime_text_to_audio "Tell me a fun fact about octopuses."
```

Terminal

```bash
uv run -m pydantic_ai_examples.realtime_text_to_audio "Tell me a fun fact about octopuses."
```

The streamed PCM audio is saved to `realtime-response.wav` so you can listen to the result afterwards. If the turn completes without audio, the script raises an error and does not create an empty WAV file.

## Example Code

realtime\_text\_to\_audio.py

```py
from __future__ import annotations

import asyncio
import sys
import wave

import logfire

from pydantic_ai import Agent, PartDeltaEvent, SpeechPartDelta
from pydantic_ai.realtime import RealtimeTurnCompleteEvent
from pydantic_ai.realtime.openai import OpenAIRealtimeModelSettings

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured
logfire.configure(send_to_logfire='if-token-present')
logfire.instrument_pydantic_ai()

# OpenAI's realtime models speak in 24 kHz mono PCM16 audio.
SAMPLE_RATE = 24000

DEFAULT_PROMPT = 'Tell me a fun fact about octopuses.'
OUTPUT_PATH = 'realtime-response.wav'

agent = Agent(
    instructions='You are a friendly voice assistant. Keep your replies short and conversational.'
)


def save_wav(path: str, audio: bytes) -> None:
    """Wrap the streamed raw PCM16 audio in a WAV container so it can be played back."""
    with wave.open(path, 'wb') as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit samples
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(audio)


async def main(prompt: str, output_path: str) -> None:
    audio = bytearray()

    async with agent.realtime(
        'openai:gpt-realtime',
        model_settings=OpenAIRealtimeModelSettings(openai_voice='marin'),
    ).session() as session:
        # Sending text (rather than audio) into an OpenAI realtime session asks the model to respond
        # right away -- with speech, since a session's default output modality is audio.
        await session.send(prompt)

        print(f'you: {prompt}')
        print('assistant: ', end='', flush=True)
        async for event in session:
            match event:
                case PartDeltaEvent(delta=SpeechPartDelta() as delta):
                    # Deltas carry raw PCM16 audio for playback and/or incremental transcript text.
                    if delta.audio_chunk:
                        audio.extend(delta.audio_chunk)
                    if delta.transcript_delta:
                        print(delta.transcript_delta, end='', flush=True)
                case RealtimeTurnCompleteEvent():
                    # The model finished speaking; this was a one-shot request, so we're done.
                    break
                case _:
                    pass
        print()

    if not audio:
        raise RuntimeError('The realtime response completed without any audio')

    save_wav(output_path, bytes(audio))
    print(f'\nSaved {len(audio)} bytes of audio to {output_path}')


if __name__ == '__main__':
    prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT
    asyncio.run(main(prompt, OUTPUT_PATH))
```

---
