# trace-it

Turn operating policy into deterministic decision processes, with reliable ingestion of
any document and AI-augmented decision-making under human control.

Describe a process in plain language, provide documents in any format, and connect its data
sources. trace-it reads the material and proposes the outcomes, inputs, source bindings, and
rules that make the process explicit. A manager reviews the proposal, then publishes it as a
versioned process definition.

AI helps formalize the process, extract evidence, explain exceptions, and propose changes.
Agents write and test the rule code. A deterministic engine applies it to every case. When
data is missing, rules conflict, or a rule cannot be evaluated, the case goes to a person.
Their resolution can produce a proposed rule change for the manager to review, preview
against past decisions, and publish. No LLM decides, and history is never rewritten.

[Open the live demo](https://gex-dashboard.hopto.org/nexia/trace-it/) ·
[Browse the API](https://gex-dashboard.hopto.org/nexia/trace-it/api/docs)

## How it works

1. **Describe.** A manager explains the process and provides policies, examples, documents
   in any format, and data sources.
2. **Formalize.** Agents propose a process definition with decision types, symbols, source
   bindings, and plain-language rules. The manager reviews every part.
3. **Publish.** Agents compile the rules to tested Python. The manager previews their effect
   on past cases and publishes one complete version.
4. **Run.** The engine evaluates each case in a sandbox and records the result, evidence,
   rule versions, and source snapshots. Uncertain cases go to a person.
5. **Improve.** Human resolutions and new evidence can become proposed process changes.
   Nothing changes until a manager reviews and publishes a new version.

The first process pack handles the invoice-payment challenge from "500 Sombras de Alberto".
The same application also runs hiring screening and other process packs without changing the
engine.

## See it in action

| Invoice queue | Document review |
|---|---|
| [![Invoices waiting for review](docs/img/invoice-review-queue.png)](docs/img/invoice-review-queue.png) | [![Invoice document with extracted fields and review controls](docs/img/invoice-document-review.png)](docs/img/invoice-document-review.png) |
| Decision evidence | Another process, same engine |
| [![Completed invoice decision with its symbols and evidence](docs/img/invoice-decision-evidence.png)](docs/img/invoice-decision-evidence.png) | [![Hiring screening process dashboard](docs/img/hiring-screening-dashboard.png)](docs/img/hiring-screening-dashboard.png) |

## What stays under human control

- Agents may propose process definitions, rule code, tests, and later changes.
- A manager decides what becomes active and resolves escalated cases.
- The engine alone decides routine cases from the published rules and immutable source
  snapshots.
- Every decision keeps its evidence and exact rule version. New versions never alter old
  decisions.

## Repository map

- `backend/app/features/` contains the API by domain feature.
- `frontend/` contains the manager console.
- `processes/` contains versionable process packs and their rules.
- `docs/adr/` records the architectural decisions.

Start with [the five key decisions](docs/key-decisions.md) for the architecture, or read the
[process-pack guide](processes/README.md) to define another process.
