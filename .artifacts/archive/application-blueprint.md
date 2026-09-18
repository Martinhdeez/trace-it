# trace-it: application blueprint

**Status:** living draft. We iterate until the blueprint is complete.
**Markers:** [DECIDED] agreed by the team · [PROPOSED] suggestion pending validation · [OPEN] undecided · [DISCARDED] considered and rejected · [PENDING] section still to write.

## 1. Vision

trace-it automates decision processes of any kind. A decision process always has the same shape:

1. **Inputs and sources of truth:** the cases to decide (documents, records) and the reference data they are checked against (spreadsheets, external systems).
2. **Deterministic rules** that must hold, written as text.
3. **A final decision** among the decision types the process defines, some of which may require a human.

From the text of each rule, agents generate deterministic functions that apply it. Those functions decide, never an LLM, and only among the decision types configured for that process. Everything specific to a process (sources, symbols, rules, decision types) is data, not code. [DECIDED]

**First process: invoice payment (the "500 Sombras de Alberto" challenge).** It decides whether to pay each of Alberto's invoices:
1. Inputs: invoice PDFs; sources: the supplier and order workbook, and the ERP.
2. Rules: the payment policy.
3. Decision types: PAGAR, NO_PAGAR or ESCALAR (the last one requires a human).

It is the process we show in the demo and the one that produces the challenge submission, but it is an instance of the product, not its definition. [DECIDED]

The application improves with use. Every human decision on a case the rules do not cover becomes a new rule. The system grows more autonomous and needs people less over time. [DECIDED]

## 2. Concepts

| Concept | What it is | Example in the invoice process |
|---|---|---|
| Process | Complete definition: sources, symbols, rules and decision types | "Invoice payment" |
| Source of truth | Reference data used for checks. Each load is stored separately; the current one is the latest by name | Supplier and order workbook, ERP |
| Instance | Each case the process decides. It has a name and a source file | An invoice PDF |
| Instance status | `PENDING` (undecided), `REVIEW` (internal state: extraction or rules disagree; not a decision) or `DECIDED` | |
| Symbol | Named datum the rules use | `issuer_nif`, `iban`, `purchase_order`, `total`, ERP status |
| Rule | Deterministic condition over the symbols and the sources. It is a requirement or a prohibition (P19); when it fires, it produces its assigned decision type and a reason | "Invoice IBAN ≠ master IBAN" |
| Decision type | Possible outputs of the process. Each process defines them, with their priority, which one is the default and which ones require a human (`requires_human`) | PAGAR, NO_PAGAR, ESCALAR (the last with `requires_human`) |
| Decision | Result recorded for an instance, with the result of each rule. Rows are only appended; the current one is the latest | |
| Finding | Past decision that a new rule says was wrong. It only warns; it does not change the past (P14) | Invoice paid when it should not have been |
| Manager | User with the `manager` role: resolves the cases that require a human and activates rules. All other users are `operator` | Alberto |

## 3. Life cycle of a process

### 3.1 Create the process [DECIDED]
1. The user uploads all relevant data: documents, spreadsheets, access to systems.
2. Optionally, they add natural-language text for whatever the data does not cover.
3. From all of that, the system derives:
   - the required **symbols**,
   - the **rules**,
   - the **decision types**.

### 3.2 Compile the rules to code [DECIDED]
Deciding must be fully deterministic, and rules must be able to change without breaking the system. So rules are not interpreted at runtime: they are turned into code.

There are two different agents:
- **Compiler agent.** Reads a rule and writes the deterministic code that applies it. It runs automatically every time a rule is added or changed: the interface chains "create rule" and "compile" (`POST /rules/{rule_id}/compile`) and shows progress, because compiling takes 30-60 s due to the LLM calls. [DECIDED]
- **Decider (engine).** For each instance, runs the code of every active rule and resolves one of the process's decision types (P19). It sticks to the code's output and uses no LLM (see P7).

The same instance with the same rules therefore always gives the same result.

Rule code contract [DECIDED, details in P18]:
- It is a pure function: it receives the instance's symbols, the sources and the other instances, and returns whether the rule fires and a reason code. The code does not return the decision: the rule sets it.
- No network, disk, clock or randomness. The cut-off date comes in as a symbol.
- It is stored next to the rule text it comes from, with a hash of text and code.

Validation before activating new code [DECIDED, details in P9 and P21]:
1. Two agents each generate code and test cases from the rule text.
2. Both codes must pass every case and agree on the whole history.
3. It runs against the history and shows which decisions change (see P2).
4. The manager approves. Only then does the rule become active.

If validation fails, the previous rule stays active and the process does not stop.

### 3.3 Run
For each instance, the system extracts the symbols, runs the code of the active rules and decides. If no rule fires, the process's default type applies. The instance goes to the manager's queue if the decision is of a type with `requires_human` or if it ends up in `REVIEW` (P21). [PENDING: details; see `.artifacts/specs/2026-09-18-reglas-sistema.md` for extraction, ERP and resilience]

### 3.4 Assisted escalation [DECIDED]
An instance is escalated when its decision is of a type with `requires_human` or when it is in `REVIEW`. The manager sees:
- the case and why it was escalated,
- **the decision the agent would take and its reasoning**,
- **the new rule the agent proposes** to resolve only similar future cases.

The manager has two options:
- **Accept:** takes the same decision as the agent and adds the proposed rule.
- **Reject:** takes their own decision and writes their own rule.

Either way a new rule enters the process. That is why the process learns continuously.

### 3.5 Self-correction through review [DECIDED]
The manager can review any decided instance, not only the escalated ones. If they find a mistake, they explain why it happened. The process corrects itself from that explanation.
[PROPOSED] Use the same mechanism as escalation: the agent turns the explanation into a rule change and the manager approves it.

### 3.6 Decision log and checking new rules [DECIDED]
Every rule is applied to every instance, with deterministic functions. Every decision is recorded. When a new rule comes in, it is re-run over past decisions to check that everything still holds.

[PROPOSED] What each decision stores:
- Instance: identifier and file hash.
- **Symbols used**, with the exact value and its origin (text of the file or the source it comes from; for an external system, with the query date).
- Version of the rule set and the result of each rule (holds or not, reason code).
- Final decision and who took it: engine or manager.
- Whether a human validated or corrected it: correct decision and reason.

Storing the symbols makes it possible to repeat the decision without re-reading the file or querying external systems. So the check is fast, free and always gives the same answer.

[PROPOSED] Result of checking a new rule, per instance:
- **Unchanged:** the decision is the same.
- **Conflict:** changes a decision a human already validated. Blocks activation until the manager resolves it (P15).
- **Change to review:** changes a decision nobody validated. Shown to the manager before activation.

### 3.7 Retroactive audit [DECIDED]
There is a history of every decision, taken by the engine or by people. Every time a rule is added, the history is reviewed to see whether any past decision was wrong according to the new rule. In the invoice process, for example:
- an invoice that was paid and should not have been,
- an invoice that was not paid and should have been.

### 3.8 Processes and rule versioning [DECIDED]
- **Process:** like a folder that contains rules. Rules can be added and removed inside it.
- Each process has **its own decision history** and **its own rule versioning**. You can go back to an earlier version or forward to a later one, like a simplified git.
- To apply completely different rules, create an **independent process**.
- When running, you choose which process to apply. Processes share neither rules nor history.

Details in P11 to P16.

## 4. Open questions (with recommendation)

**P1. What shape does a new rule take?** [DECIDED]
The rule is written as text. The application generates the code that applies it underneath, automatically. See P8.

**P2. Does a new rule also apply to the past?** [DECIDED]
Yes, as a check: before activating it, it runs against every recorded decision (see 3.6). The manager confirms after seeing the impact.

**P3. What happens when two rules clash?** [DECIDED]
- **At runtime:** if several rules fire with different decisions, the process's highest-priority decision type wins (P19). It does not escalate.
- **When adding a rule:** if it clashes with another active rule, the system warns and the rule does not go in until the manager resolves it (P21), for example by rewriting one of the two.

**P4. Decisions that require a human, and the challenge filter.** [DECIDED]
- A type with `requires_human` (ESCALAR for invoices) is a valid process output: a rule may give it as the correct answer. The manager's later resolution is stored separately and does not change that output.
- We know which rules each decision was taken with, so later learning does not alter what was already decided.
- Full versioning belongs to iteration 2.
- The application exports, per instance, its name and its decision. `outcomes.jsonl` (`{"file_id", "result"}`) is only the format the challenge asks for that export, not an application concept. [DECIDED]
- [PROPOSED] In iteration 1, each decision stores the code hash of every rule applied. It is cheap and, in iteration 2, lets us link old decisions to their version.

**P5. Who validates the generated process when it is created?** [OPEN]
Recommendation: the user reviews the extracted symbols, rules and decision types before the first run. Each rule shows where it comes from (a workbook sheet, a sentence of the text). A reading error that slips through here repeats in every instance.

**P6. How are symbols that need external systems represented?** [OPEN]
Recommendation: each source of truth is a connector with a fixed contract (what data it gives and how it fails). The challenge ERP is the first connector. This is what makes the system reusable for other processes.

**P7. Is the decider agent an LLM?** [DECIDED: no]
If an LLM chose which rule to apply, the choice would not be deterministic and it could skip a rule that did apply.
Decision:
- **The code of every active rule always runs** on each instance; nobody picks which.
- Results are combined by the priority of the process's decision types (P19). For invoices: ESCALAR > NO_PAGAR > PAGAR.
- The "decider agent" is that engine, without an LLM.
- The LLM only steps in afterwards: it explains the decision and, if the instance is escalated, proposes a decision and a rule (3.4).

**P8. Free code or a rule language?** [DECIDED: free code]
- The compiler agent generates **Python code** for each rule, fully automatically.
- Reason: rules change all the time (added, removed, modified) and the application must keep working without anyone touching its code. It must also serve any process, not just invoices. A closed catalogue of primitives would force us to program every new kind of rule.
- The primitives catalogue (rules as data) is discarded for that reason.

[DECIDED] Safe execution of generated code (an LLM wrote it; implemented in `features/agents/sandbox.py`):
- Static check before accepting it: only allowed imports (`decimal`, `datetime`, `re`, `math`, `unicodedata`) and no `open`, `exec`, `eval`, `__import__` or network access.
- Execution in a separate process, with a time limit, no network and no disk.
- The function returns a fixed-shape result: `{fires, reason}` (P18). If it returns anything else, fails or times out, the instance goes to `REVIEW` with the reason (P21). We never decide without that rule.

**P9. How do we know the generated code is correct?** [DECIDED]
1. Two independent agents (different models where possible). Each writes, from the rule text alone, its code and its tests: code A + tests A, code B + tests B. Neither sees the other's work.
2. **Every test runs against both codes**: the cross (A with tests B, B with tests A) catches differences in interpretation; each agent's own tests catch programming errors.
3. Both codes must agree on every instance in the history.
4. The manager reviews the impact and activates.
5. In production both codes run. If they disagree on an instance, the instance goes to `REVIEW` with the reason (P21).

If a test fails, we do not know who is right (code or test). The manager resolves it, usually by clarifying the rule text and recompiling. Cost: two compilations per rule change, not per instance.
Limit: if both agents misread an ambiguous text the same way, it gets through. The impact review (step 4) covers it.

**P10. What if a new rule uses a symbol that was not stored?** [OPEN]
For example, for invoices, a new rule about the "financial surcharge" needs a field that was not extracted before.
The full text of each file is always stored already (F2, `files.text`). Recommendation: if a symbol is missing, extract it from the stored text (without re-reading scans) and record it as a new symbol before checking the rule. If the datum comes from an external system, use the stored load of that source, not the live system.

**P11. What do we call the unit?** [DECIDED]
**Process.** There is no "project". See 3.8.

**P12. When do we create a new process and when a new version?** [DECIDED]
- **New version:** rules are added, removed or changed within the same process. Invoice example: policy v3 → policy v4.
- **New process:** completely different rules. An independent process, with its own history.
- [PROPOSED] A new process can be created by copying another one's rules, but its history starts empty.

**P13. What is a version and how do we "go back"?** [DECIDED]
- Versioning is linear: a log of the process's rule changes.
- Each change creates a new immutable version with the full snapshot of the rules, who made it, the reason and the instance that triggered it, if any.
- "Going back" activates an earlier version. It deletes nothing and is recorded as one more step.
- There is only one active version per process. New instances are decided with it.

**P14. What does the retroactive audit do with a past decision that now comes out differently?** [DECIDED]
**It never changes the past.** It only warns: it produces information about wrong past decisions (findings); for invoices, for example, "paid when it should not have been" or "not paid when it should have been". With that, the company decides what to do (for invoices, claim the money back or pay what is owed). Handling that warning is outside the system.

**P15. If the new rule contradicts a decision a person validated, who wins?** [DECIDED]
Neither, automatically. It is marked as a conflict and the manager resolves it.

**P16. Are data (files, sources) versioned too?** [DECIDED: no]
- Ingested files have no versions: they are stored as-is and do not change. What changes are the decisions about them.
- Each decision in the history is linked to the files it was taken with.
- If a file is modified, it is treated as a new file. It is identified by its content hash.
- [PROPOSED] An external system (the ERP for invoices) is not a file but a live system. Each download is stored as one more load of the source, with its date, just like a new file. So the previous rule applies to it too.

**P17. Compare any two versions?** [DISCARDED]
Not needed as a feature of its own: just run one version and then the other.

**P18. Data the rule function receives.** [DECIDED]
One signature for every rule and every process:
```python
def evaluate(instance: dict, sources: dict[str, list[dict]], others: list[dict]) -> dict:
    # returns {"fires": bool, "reason": str}
```
- `instance`: the instance's symbols.
- `sources`: latest load of each source, by name (for invoices: suppliers, orders, local ERP snapshot).
- `others`: symbols of the process's other instances, for rules across instances (for invoices: "duplicate order").
Pure function: no network, no disk, no clock.
The code does not return the decision: the rule sets it in its definition (field `decision`), which a person approves. The code only says whether it fires and why.

**P19. Rule types and combination.** [DECIDED]
Every rule runs on each instance. There are two types:
- **Requirement:** something that must hold. If it does not, the rule fires. Invoice example: "the IBAN matches the master IBAN".
- **Prohibition:** something that must not happen. If it does, the rule fires. Invoice example: "the ERP says PAGADA".
Each rule declares which decision it produces when it fires. If none fires: the process's default decision. If several fire: the highest priority wins.

**Decision types configurable per process [DECIDED].** No decision name is fixed in code. Each process defines its types with:
- `priority`: the highest wins when several rules fire;
- `is_default`: exactly one, applied when none fires;
- `requires_human`: instances with that decision go to the manager's queue and the assistant proposes how to resolve them.
In the invoice process: ESCALAR (3, requires a human) > NO_PAGAR (2) > PAGAR (1, default).

**P20. Symbol extraction.** [DECIDED]
- Each process defines its list of symbols (name, type, description).
- An LLM fills it with structured output: from the file text, or from the image for a scan. No per-template parsers.
- Two independent extractions (different LLM providers) must agree. On top of that, fixed validators where they apply (for invoices: IBAN mod-97, NIF check letter, base + VAT = total).
- If they disagree or a validator fails: status `REVIEW` (P21). A validator failure is never fed back to the model to fix: it would learn to give a value that adds up instead of the one on the document.
- Each file is extracted only once (by its hash) and the symbols are stored; repeating decisions or audits does not call the LLM again.

**P21. Discrepancies.** [DECIDED]
- **When adding a rule:** if the two codes disagree, or clash with another rule or with a validated decision, the system detects it, warns the user, and the rule **does not go in** until it is resolved.
- **At runtime:** if the two extractions disagree, or the two codes of an already accepted rule disagree or fail on an instance, the instance goes to `REVIEW`. `REVIEW` is an internal instance state, not a decision: it is not one of the process's decision types (for invoices, it is not ESCALAR). Export is blocked while any instance is `PENDING` or in `REVIEW`.

**P22. LLM providers.** [DECIDED]
- The system depends on no provider. Any API (Anthropic, OpenAI, Gemini, local...) can be used.
- Each role has its own configuration, changeable at runtime: `compiler_a`, `compiler_b`, `extractor_1`, `extractor_2`, `assistant` (and `corrector` in iteration 2). Each picks a model chain (the first model and its fallbacks if a provider fails), its settings, retries, request limit and prompt.
- [DECIDED] Implementation: PydanticAI (P23). Configuration comes from presets in the repo and is stored in the database as append-only versions (`agent_config`); every call uses the active version of its role and records it in the trace. Details in `docs/agents-plan.md`.
- By default, paired roles (`_a`/`_b`, `_1`/`_2`) use different providers, in their fallback models too, so they do not make the same mistakes.

**P23. Agent framework: PydanticAI.** [DECIDED]

*Context.* The agents (compilers A and B, assistant, extractors and, in iteration 2, the corrector) called the LLMs through our own client on top of LiteLLM: structured output validated by hand, a repair loop written for each agent, no provider switch when one goes down, and tests that patch the client. We wanted the same things in every agent: typed output, bounded retries with the error sent back to the model, a fallback model chain, usage limits, cost per call and tests without network. All of it without tying ourselves to a provider (P22) and without moving flow control out of our code: the instance and rule state machines, the manager's queue and idempotency already live in Postgres.

*Alternatives.*

| Option | Why not |
|---|---|
| Plain LiteLLM (what we had) | Gives a common interface, but everything else (output validation, retry with the error, fallback chain, limits, tests) must be written in each agent. We already had two different repair loops |
| LangGraph | Its value is a graph with its own state and persistence. It would duplicate what is already in Postgres and take flow control out of our code |
| Claude Agent SDK / OpenAI Agents SDK | Each is built for its own provider; clashes with P22 and with paired roles using different providers |
| CrewAI | Models teams of agents with roles and tasks that coordinate themselves. Our agents do not talk to each other: the code fixes the flow and the LLM never decides (P7) |
| **PydanticAI** | Chosen |

*Decision.* Every agent is written with PydanticAI v2 (`pydantic-ai-slim`, extras `openai`, `anthropic`, `google`):
- one `Agent` per agent type, with a typed `output_type`;
- `output_validator` + `ModelRetry` where the error helps the model correct itself: the compiler (sandbox and its own tests) and the assistant (decision within the process's types). Never in extraction (P20);
- `FallbackModel` with each role's model chain, `UsageLimits` and a per-request `timeout`;
- each role's configuration lives in repo presets (`agents/presets/*.json`) and in append-only versions in `agent_config`, editable at runtime without a restart;
- every run leaves an event in `events` with the configuration version, the model that answered, the prompt hash, tokens, cost, latency and retries;
- tests with `FunctionModel`/`TestModel` and `agent.override`, without real calls.
We do not use its graphs, its durable execution or its tools with human approval: flow, state and approval already live in our code and in Postgres.

*Consequences.*
- `features/llm/client.py`, `llm_config` and the `/llm/config` endpoints go away, replaced by `agent_config` and `/agents/.../config` (the frontend changes endpoint).
- Model names move from the LiteLLM format (`anthropic/claude-opus-5`) to the PydanticAI one (`anthropic:claude-opus-5`). The Gemini key is called `GOOGLE_API_KEY`.
- Configurations can be compared with data: every result points to the exact version that produced it.
- New, fast-changing dependency: the version is pinned (`>=2.45,<3` and `uv.lock`) and the local docs live in `.context/pydantic-ai/` so we do not code against old APIs.
- Risk: if every model in a chain fails, the agent fails closed (the rule is not activated, the instance stays in `REVIEW`); it never decides.

*Evidence.* The APIs used are checked against the local PydanticAI v2 docs (references by section in `docs/agents-plan.md` §12). The comparisons with LangGraph, CrewAI and the Claude and OpenAI SDKs are in those same docs and Pydantic writes them, so they are read with that bias in mind; the underlying reason for discarding them is our architecture (P7, P22 and state in Postgres), not those tables. Cost and latency figures per stage will come from `GET /processes/{process_id}/metrics` over `events` (plan, §7.4).

## 5. First-iteration features [PROPOSED; F11 cut DECIDED]
Goal of iteration 1 (Saturday ~14:00): a correct `outcomes.jsonl` for batch 1 and the whole rule cycle working end to end in one process.

| # | Feature | What it does | In v1 |
|---|---|---|---|
| F1 | Processes | Create, list and select processes. Each with its rules, versions and history | Yes |
| F2 | Ingestion | Upload files. Identified by hash; stored as-is with the full extracted text (PDF text, or OCR/vision for scans) | Yes |
| F3 | Connectors | Spreadsheets and external systems (for invoices: master workbook and ERP, with a fault-tolerant API). Each load or download is stored separately | Yes |
| F4 | Symbol extraction | Pulls from each instance the symbols the rules use, with their origin | Yes |
| F5 | Rules and compiler | Add a rule as text; two agents generate code and tests; cross-tests, agreement on the history; activated if there are no discrepancies (P9, P21) | Yes |
| F6 | Engine | Runs every active rule on each instance, applies decision-type priority and records the decision. No LLM | Yes |
| F7 | History and audit | Log of every decision. Activating a version re-runs it over the history: changes, conflicts and findings | Yes |
| F8 | Assisted escalation | Manager's queue (types with `requires_human` and `REVIEW`). The agent suggests a decision, reasoning and rule; the manager accepts or writes their own | Yes |
| F9 | Versioning | Linear list of versions; activate an earlier one | Iteration 2 [DECIDED] |
| F10 | Export | Download each instance's name and decision. For invoices, in the challenge format (`outcomes.jsonl`) | Yes |
| F11 | Create process from data | From all uploaded data and free text, derives symbols, rules and decision types | Iteration 2 |
| F12 | Self-correction through review | The manager flags a mistake in a decision and explains why; the agent proposes the rule change | Iteration 2 |

Reason for the cut: F11 is the hardest to make reliable and is not needed to pass the filter. In v1, the rules of policy v3 are added one by one through F5. That way the product's own flow produces the submission.

## 6. Architecture [PROPOSED]

**Stack [DECIDED]:** Python backend with FastAPI; PostgreSQL database. Frontend chosen by Carlos.

### 6.1 Components
| Component | Responsibility | Uses an LLM? |
|---|---|---|
| Store | PostgreSQL: users, processes, decision types, symbols, sources, files, instances, extractions, rules, decisions, findings, events, versioned agent configuration (`agent_config`); rule versions: iteration 2 | No |
| Ingestion | Hash, file storage, text extraction | Only for scans (vision) |
| Connectors | Spreadsheets and external systems. An external system's client handles authentication, retries, rate limits and outages (for invoices: the ERP) | No |
| Symbol extractor | Instance text + sources to symbols with origin | Yes (double extraction, P20) |
| Compiler | Rule text to code + tests | Yes |
| Engine | Runs the code of every rule and decides | **No** |
| Auditor | Re-runs a version over the history and classifies the differences | No |
| Escalation assistant | Suggests a decision, reasoning and rule for an escalation | Yes |
| API + web | Manager's interface | No |

Principle: the LLM is never on the decision path. It only writes rule code, extracts symbols and makes suggestions to the manager.

**Agent layer [DECIDED, P23].** The components that use an LLM (extractor, compiler, assistant) are PydanticAI agents on shared infrastructure (`features/llm/`): the model for each call is built from the active version of its role in `agent_config` (fallback model chain, settings, retries, limits and prompt), and every run leaves an event in `events` with that version, the model that answered, tokens, cost and latency. Each LLM result (symbols per file, code per rule) is computed once and stored; deciding and auditing do not call the LLM again. Execution plan: `docs/agents-plan.md`.

### 6.2 Flow of an instance
1. Ingestion: file → hash → full text stored.
2. Extraction: text + sources → symbols with origin.
3. Engine: symbols + code of the active version → result of each rule → decision.
4. Record: decision with symbols, version and the result of each rule.
5. If the decision is of a type with `requires_human`, or the instance ends up in `REVIEW` → manager's queue with the assistant's suggestion.

### 6.3 Flow of a rule change
1. Rule text (written by the manager or proposed by the assistant).
2. The compiler generates code and tests.
3. The code passes its tests and every human-validated decision.
4. The auditor re-runs over the history: unchanged, change to review, conflict and findings.
5. The manager approves → new active version.

## 7. Pending [PENDING]
- Manager's interface (screens).
- Traceability: event format and how to query "why was X decided".
- Fit with the rubric and list of ADRs.
- Frontend.

The division of work is in `docs/mvp-plan.md` and `docs/team-guide.md`.
