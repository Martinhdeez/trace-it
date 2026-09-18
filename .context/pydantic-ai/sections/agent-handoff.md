# [Agent Handoff](https://pydantic.dev/docs/ai/examples/realtime/realtime-handoff/)

# Agent Handoff

Realtime speech-to-speech models are great conversationalists, but they don't produce structured output. This example shows the robust pattern: let the realtime model run the live conversation, then hand its [message history](https://pydantic.dev/docs/ai/core-concepts/message-history/) to a normal [`Agent.run()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) with `output_type` to extract a typed result.

Because a [realtime session](https://pydantic.dev/docs/ai/realtime/overview/) records the _same_ [`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage) history a text agent produces, the handoff is just passing [`session.all_messages()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.all_messages) along -- realtime and non-realtime runs are peers that interoperate through message history.

Demonstrates:

-   [realtime sessions](https://pydantic.dev/docs/ai/realtime/overview/)
-   [structured output](https://pydantic.dev/docs/ai/core-concepts/output/) via a text-agent handoff
-   [message history](https://pydantic.dev/docs/ai/core-concepts/message-history/) shared across realtime and non-realtime runs

The example models a short support call: a caller describes a problem to the realtime voice agent, then the accumulated conversation is handed to a text agent that distills it into a typed `SupportTicket`. The caller's side is driven with text turns so the example runs without a microphone -- a real app would stream microphone audio with [`send_audio()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.send_audio) instead (see the [voice assistant example](https://pydantic.dev/docs/ai/examples/realtime/realtime-voice/)).

The handoff only runs after every scripted caller turn receives a [`RealtimeTurnCompleteEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeTurnCompleteEvent). If the realtime connection ends early, the example raises an error rather than creating a ticket from a partial call.

## Running the Example

Both the realtime `gpt-realtime` model and the text triage agent run on OpenAI, so you'll need an OpenAI API key set via `OPENAI_API_KEY`.

With [dependencies installed and environment variables set](https://pydantic.dev/docs/ai/examples/setup/#usage), run:

-   [pip](#tab-panel-52)
-   [uv](#tab-panel-53)

Terminal

```bash
python -m pydantic_ai_examples.realtime_handoff
```

Terminal

```bash
uv run -m pydantic_ai_examples.realtime_handoff
```

## Example Code

realtime\_handoff.py

```py
from __future__ import annotations

import asyncio
from typing import Literal

import logfire
from pydantic import BaseModel

from pydantic_ai import Agent, PartEndEvent, SpeechPart
from pydantic_ai.realtime import RealtimeTurnCompleteEvent

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured
logfire.configure(send_to_logfire='if-token-present')
logfire.instrument_pydantic_ai()


class SupportTicket(BaseModel):
    """The structured ticket distilled from the spoken support call."""

    summary: str
    category: Literal['hardware', 'software', 'billing', 'other']
    priority: Literal['low', 'medium', 'high']
    follow_up_questions: list[str]


# The realtime model runs the live conversation.
voice_agent = Agent(
    instructions='You are a friendly, concise phone support agent. Ask one question at a time.'
)

# A normal text agent turns the finished conversation into a typed result -- something a realtime
# model can't do itself.
triage_agent = Agent(
    'openai:gpt-5.2',
    output_type=SupportTicket,
    instructions='Summarize the support call as a structured ticket.',
)

# What the caller "says" -- each line is one spoken turn, driven as text so the example runs without
# a microphone.
CALLER_TURNS = [
    "Hi, my laptop won't charge anymore -- the light doesn't come on when I plug it in.",
    'I already tried a different outlet and it still does nothing. I need it for a presentation tomorrow.',
]


async def main() -> None:
    async with voice_agent.realtime('openai:gpt-realtime').session() as session:
        # A session is consumed with a single event loop. We drive the caller's turns from inside it:
        # send the first line, then send the next one each time the model finishes a turn.
        remaining_turns = iter(CALLER_TURNS)
        first_turn = next(remaining_turns)
        print(f'caller: {first_turn}')
        # Sending text into an OpenAI realtime session asks the model to respond right away.
        await session.send(first_turn)

        async for event in session:
            match event:
                case PartEndEvent(
                    part=SpeechPart(speaker='assistant', transcript=transcript)
                ) if transcript:
                    print(f'agent: {transcript}')
                case RealtimeTurnCompleteEvent():
                    next_turn = next(remaining_turns, None)
                    if next_turn is None:
                        break  # The caller has said everything; end the call.
                    print(f'caller: {next_turn}')
                    await session.send(next_turn)
                case _:
                    pass
        else:
            # The event stream ended without the `break` above, i.e. before the call completed.
            raise RuntimeError(
                'The realtime session ended before the support call completed'
            )

        # The realtime session recorded ordinary `ModelMessage` history; hand it off to the text
        # agent, which can do the structured extraction the realtime model can't.
        handoff_history = session.all_messages()

    ticket = await triage_agent.run(
        'Create the support ticket for this call.', message_history=handoff_history
    )
    print(f'\nStructured ticket:\n{ticket.output.model_dump_json(indent=2)}')


if __name__ == '__main__':
    asyncio.run(main())
```

---
