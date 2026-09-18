# [Pydantic AI vs LiveKit Agents](https://pydantic.dev/docs/ai/comparisons/vs-livekit/)

# Pydantic AI vs LiveKit Agents

LiveKit Agents is a voice-agent framework built on LiveKit's WebRTC transport: rooms, SIP telephony, turn detection, noise cancellation, mid-call handoffs, and plugins for STT, LLM and TTS vendors, with a cascaded pipeline as the default. Pydantic AI's [realtime support](https://pydantic.dev/docs/ai/realtime/overview/) is a speech-to-speech agent loop on four providers behind one API, and it is the same typed [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent) that runs as text, in a [web chat](https://pydantic.dev/docs/ai/guides/web/) or behind your API: the call uses the same tools, dependencies and [capabilities](https://pydantic.dev/docs/ai/realtime/capabilities/), becomes ordinary message history you can [hand to a text agent](https://pydantic.dev/docs/ai/realtime/history/#handing-off-to-a-text-agent) for structured output, and is traced end to end in [Logfire](https://pydantic.dev/logfire). You bring the transport; with LiveKit, the transport is the product.

Pydantic AI is one part of a stack: the [Harness SDK](https://pydantic.dev/docs/ai/harness/) for capabilities and complete agents, [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/), [Pydantic Graph](https://pydantic.dev/docs/ai/graph/graph/), [Pydantic Logfire](https://pydantic.dev/logfire) for observability, and [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/) itself for validation. The tables below cover the whole of it.

## Framework

LiveKit Agents

Pydantic AI and [Harness SDK](https://pydantic.dev/docs/ai/harness/)

Language

Python (also Node)

Python

License

Apache-2.0

MIT

Model providers

Many (plugins)

[Many](https://pydantic.dev/docs/ai/models/overview/)

Extensibility

Pipeline nodes (`stt_node`, `llm_node`, ...)

[Capabilities and toolsets](https://pydantic.dev/docs/ai/guides/extensibility/); [50+ with the Harness SDK](https://pydantic.dev/docs/ai/harness/)

Harnesses

Build your own

Built-in [`Coder`](https://pydantic.dev/docs/ai/harness/coder/) and [`Researcher`](https://pydantic.dev/docs/ai/harness/researcher/), or compose your own

Observability

OpenTelemetry

[OpenTelemetry](https://pydantic.dev/docs/ai/integrations/logfire/#using-opentelemetry), including [Pydantic Logfire](https://pydantic.dev/logfire)

Durable execution

No

[5+ integrations](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/)

Interfaces

WebRTC rooms, telephony, text sessions

[CLI](https://pydantic.dev/docs/ai/integrations/cli/), [web chat](https://pydantic.dev/docs/ai/guides/web/), [AG-UI](https://pydantic.dev/docs/ai/integrations/ui/ag-ui/), [Vercel AI](https://pydantic.dev/docs/ai/integrations/ui/vercel-ai/), [ACP](https://pydantic.dev/docs/ai/harness/acp/) (experimental)

Realtime voice

Speech-to-speech and cascaded STT + LLM + TTS

[Speech-to-speech](https://pydantic.dev/docs/ai/realtime/overview/), four providers

Evals

Yes

[Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/)

Image generation

No

[Image Generation](https://pydantic.dev/docs/ai/guides/image-generation/)

## Realtime, side by side

Our realtime support means speech-to-speech models: one persistent connection, audio in and audio out, on the four providers below. LiveKit also runs the cascaded pipeline, which we do not. If you are choosing a voice stack, these are the rows that decide it:

LiveKit Agents

Pydantic AI

Speech-to-speech providers

Plugins for several providers

[Four](https://pydantic.dev/docs/ai/realtime/overview/#provider-support) behind one API: OpenAI, Azure OpenAI, Gemini Live, xAI; ElevenLabs in [#7964](https://github.com/pydantic/pydantic-ai/pull/7964)

Cascaded STT + LLM + TTS

Yes, the default; dozens of STT and TTS plugins

Not built in; [compose it yourself](https://pydantic.dev/docs/ai/realtime/overview/#other-ways-to-build-voice) around a text agent

Audio transport

WebRTC rooms via LiveKit server or Cloud

Yours: [browser WebRTC sideband or WebSocket relay](https://pydantic.dev/docs/ai/realtime/deployment/)

Telephony

SIP in and out, DTMF, transfers; numbers on Cloud

[Bridge a provider](https://pydantic.dev/docs/ai/realtime/deployment/#siptelephony-bridge) such as Twilio

Turn detection

Silero VAD, own turn-detector model, adaptive interruption

[Provider turn detection, barge-in, push-to-talk](https://pydantic.dev/docs/ai/realtime/turns/)

Noise cancellation

Krisp and ai-coustics plugins; enhanced models on Cloud

Provider-side only

Hand off to another agent mid-call

Yes, context carried over

No; [delegate from a tool](https://pydantic.dev/docs/ai/realtime/tools/#delegating-work-during-a-call) instead

Tools mid-call

`@function_tool`, MCP

[The same tools, toolsets and dependencies](https://pydantic.dev/docs/ai/realtime/tools/) as a text agent

Capabilities mid-call

No equivalent

[Capabilities and hooks](https://pydantic.dev/docs/ai/realtime/capabilities/), with documented limits

After the call

`session.history`, `SessionReport` JSON

[`Agent.run()` on the call's history](https://pydantic.dev/docs/ai/realtime/history/#handing-off-to-a-text-agent) for structured output or follow-up

Observability

OpenTelemetry; Insights on Cloud

[OpenTelemetry](https://pydantic.dev/docs/ai/realtime/observability/): session, turn and tool spans, usage attributed per response

Evals

pytest framework with an LLM judge; simulations on Cloud

[Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/) on the text hand-off; nothing realtime-specific yet

Deployment

Agent server, dispatch, jobs; Cloud or self-host

[Your process, your backend](https://pydantic.dev/docs/ai/realtime/deployment/)

The same agent without voice

Text-only sessions, still a room and a server

[`run()`, CLI, web chat, AG-UI, Vercel AI](https://pydantic.dev/docs/ai/overview/interfaces/)

---
