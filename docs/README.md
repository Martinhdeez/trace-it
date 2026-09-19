# Documentation

Start with the [root README](../README.md) for what the system does, then:

| Document | What it is |
|---|---|
| [defense.md](defense.md) | The 6-8 minute demo for the jury, step by step against the rubric, with commands and evidence |
| [CONVENTIONS.md](CONVENTIONS.md) | Language, naming and the contracts every feature shares |
| [team-guide.md](team-guide.md) | Git flow, backend layout, running and testing locally |
| [api.md](api.md) | The API, screen by screen, for whoever builds the console |
| [learning.md](learning.md) | On-demand norm proposals, validation and manager adoption |
| [decision-review.md](decision-review.md) | Optional decision advice, human approval, fallback and export behavior |
| [adr/README.md](adr/README.md) | Architecture decision records. ADR 0001 wins over everything else |
| [invoice-payment-rules.md](invoice-payment-rules.md) | Where each of the 16 invoice rules comes from, and the team decisions behind them |
| [scale-and-cost.md](scale-and-cost.md) | Measured throughput and capacity limits (engine to 50k invoices, OCR, storage), rate limits, the cost formula (tokens, infrastructure, people), four deployment scenarios and the scaling plan with triggers |
| [runbook-batch2.md](runbook-batch2.md) | Saturday's batch 2, ERP update and norm v4, step by step, with rehearsal timings |
| [mentor-questions.md](mentor-questions.md) | Open doubts about the reference outcomes, how we handle each and what flips it |
| [sources-http.md](sources-http.md) | The HTTP source connector (the ERP): configuration and guarantees |
| [process-discovery.md](process-discovery.md) | Backend workflow for discovering sources and rules through workbooks, chat and manager review |
| [ingestion/README.md](ingestion/README.md) | Document ingestion: PDF, OCR, workbook |
| [ingestion/setup.md](ingestion/setup.md) | Reproduce OCR: prerequisites, pinned downloads, provider keys and complete API commands |
| [../processes/README.md](../processes/README.md) | Format of a process pack |
| [../tools/README.md](../tools/README.md) | Production API demo with OCR, plus historical comparison tools |
| [../backend/tests/golden/README.md](../backend/tests/golden/README.md) | The golden outcomes for batch 1 |

Superseded plans and analyses are archived under [`.artifacts/`](../.artifacts/). They are
history, not guidance.

[Process versions and replay](process-versions.md): draft, validate, approve, publish and reproduce a decision.

- [Process chat](process-chat.md): discuss existing processes, propose edits and preview their impact.
