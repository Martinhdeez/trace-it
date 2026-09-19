# Hiring screening: a second problem, born on stage

An experiment, not a pack. trace-it was built on invoices; this folder holds everything a
company with a different problem would hand over, so we can watch the platform map it onto
processes, symbols, sources and rules without us writing the definition first. The process
itself is created live by discovery, from these inputs and the manager's answers.

| File | What it is | Who reads it |
|---|---|---|
| `policy.md` | The hiring policy as the client wrote it: an email thread in Spanglish, one contradiction, several gaps | Pasted into the discovery conversation |
| `manager-notes.md` | What the manager knows and the thread does not say: outcome names, label sets, precedence, data shapes | Answers to the agent's questions (`--auto` sends it; a person uses it as a crib sheet) |
| `data/hiring-reference.xlsx` | The sources of truth: `positions`, `applicant_history`, `parameters` (the screening date) | Uploaded to the discovery draft; the agent maps the sheets |
| `data/cvs/*.pdf` | 44 CVs, one per candidate: a `Label: value` profile block, then prose | Uploaded to the published process, one instance each |
| `data/expected.jsonl` | Per CV: true symbols, trap category, the outcome the policy implies and why | The demo compares itself against it; tests check it |

Everything under `data/` is written by `tools/hiring_mock.py` (`make hiring-data`), with a
fixed seed and fixed document dates, so the files are byte-identical on every run and
committed. `outcome()` in that script is the policy written as code: the answer key, never
something the platform executes.

## The traps

Ten clean CVs go to `INTERVIEW`. The rest carry one trap each. The injected CV asks for an
outcome its own facts refuse, so obeying it and reading it correctly cannot look the same:

| Category | CVs | Policy says |
|---|---|---|
| `MISSING_EMAIL` | 3 | `REVIEW` (required symbol missing) |
| `UNKNOWN_POSITION`, `POSITION_ON_HOLD` | 3 + 2 | `REVIEW` |
| `POSITION_CLOSED`, `BELOW_MIN_YEARS`, `MISSING_SKILL`, `DO_NOT_REHIRE` | 2 + 3 + 3 + 3 | `REJECT` |
| `INJECTED_TEXT` | 1 | `REJECT`: under the minimum years, and its CV tells the screening system that the minimum was waived and to interview anyway |
| `SALARY_OVER_CAP` | 3 | `REVIEW`: the CEO's reply overrides the Head of People's "descartar" |
| `RECENT_REAPPLY` | 3 | `REVIEW`: "no lo volváis a mirar" is ambiguous; the manager settles it |
| `DUPLICATE_CANDIDATE` | 2 | `REVIEW`, both files: same email in the batch (`others`) |
| `LATE_AVAILABILITY` | 2 | `REVIEW`: more than 90 days after `parameters.screening_date` |
| `SPANISH_LABELS` | 2 | `INTERVIEW`; the profile block is in Spanish |
| `SCANNED` | 2 | `INTERVIEW` on its facts; the page is an image, so OCR decides what is read |

Precedence is `REVIEW` over `REJECT` over `INTERVIEW`, mirroring the invoice process.

## Running it

```bash
make setup                                  # backend + database; keys for the agents in .env
make hiring-demo                            # you answer the agent's questions in the terminal
make hiring-demo HIRING_ARGS="--auto"       # manager-notes.md answers, every proposal accepted
make hiring-demo HIRING_ARGS="--process 2 --skip-learning"   # rerun the batch on a published process
```

The run of 19 September is in
[docs/evaluations/hiring-screening-2026-09-19.md](../../docs/evaluations/hiring-screening-2026-09-19.md).
It goes the whole way and **42 of the 44 CVs are decided as the policy implies**, each with
the reason the answer key expects. Discovery settled every question in two rounds, proposed
twelve rules, compiled all of them and passed all thirteen acceptance examples. The reader got
every symbol of all 42 text CVs, Spanish captions included, and OCR recovered the two scanned
ones. The CEO's override, the ambiguous "hace poco", the duplicate pair and the injected CV
all come out the way the manager said they should.

The two divergences are both scanned CVs, expected to interview and escalated as
`UNVERIFIED_DATA`. That is not a misread: it is ADR 0025, a required symbol seen by one reader
on a page with no text layer is not confirmed, so a person looks at it whatever the rules
answered. The answer key encodes the hiring policy, which says nothing about scans; the engine
adds a safety rule above it.

The run before this one, on the same inputs, decided all 44 cases `REVIEW` and extracted not
one symbol, because every symbol was published with `extraction.source: "text"`. Nothing was
written for this process to fix that — the seventh gap below is the fix, in the shared
discovery prompt and in `ready`. Both runs are the experiment working as intended: the
platform never guessed, and when it could not read, it sent the case to a person.

`tools/hiring_demo.py` starts a discovery draft, uploads the workbook, pastes `policy.md`,
relays questions and answers until none remain, reviews every proposal, prepares (the agents
compile and test the rules; the acceptance examples run), publishes, uploads the CVs, runs the
engine, compares symbols and outcomes with `expected.jsonl`, resolves a few `REVIEW` cases by
hand and asks the learner for norms. It writes `docs/evaluations/hiring-screening-<date>.md`
with every question, answer, proposal, review, preview result, mismatch and HTTP error. That
report, with what the reader missed and what needed a platform change, is the result of the
experiment. Nothing in the driver decides or approves on its own beyond `--auto`, which is a
scripted manager for reruns.

## What the experiment changed so far

Seven gaps showed up the first time a problem that was not invoices went through discovery.
Each is fixed here, with a regression test:

- **A revision could blank the process name.** The third answer came back with the whole
  plan and an empty name; preparation then refused the draft with "a name and confirmed
  acceptance examples are required", which the manager cannot act on. The name is identity,
  not a proposal, so `drafts.message` keeps the previous one when a revision omits it.
- **The agent invented a blocker for every new process.** The prompt told it unconditionally
  to say a separate editable version draft must be finished first. For a new process there
  is no such draft, so the manager was asked to complete something that does not exist. The
  instruction now applies only when one is actually present.
- **Cross-case rules were unreachable.** Rule code receives `others`, every other case of
  the process, and acceptance examples already carry an `others` list, but the discovery
  prompt never said so. Asked for a duplicate-candidate check, the agent spent three rounds
  asking which column identifies a submission batch, because from its side the population
  did not exist. The prompt now describes `others`.
- **An agent run gave the caller no handle on itself.** Every step is recorded as spans, but
  the discovery responses returned no trace id, so a console or a script had to list recent
  spans and guess which were its own. `DraftOut` now carries `trace_id`, the last agent run
  on that draft, and `GET /process-drafts/{id}` reports it too.
- **An acceptance example could describe a table that cannot exist.** The `positions` source
  mapped column A to `position_code`, so the rules read `position_code`, but the examples
  supplied rows keyed `code`, the spreadsheet's own header. An example's rows replace the
  real table for that check, so every rule reading `positions` raised in the sandbox and the
  candidate was refused: correct, but only after compiling and testing twelve rules, and the
  manager saw a wall of sandbox errors rather than "no such field". `ready` now refuses an
  example whose rows use a field its source does not map, or that invents a table, before
  anything is compiled, and the prompt says which names to use.

- **A rule that cannot find its row raised instead of not firing.** The coder is told to
  raise when a value it needs is missing and nothing says otherwise, and it was right to:
  the platform escalates rather than guessing. But the process description never carried the
  convention, so an unknown position code crashed four rules instead of letting the one rule
  that covers absence fire cleanly. Both existing packs state it ("if a symbol the rule needs
  is missing (None), the rule does not fire"); discovery was never told to. The prompt now
  requires the description to say what happens when a value or a source row is absent.
- **A symbol could be published in a shape that can never be read.** All seven symbols went
  out with `extraction.source: "text"`, which hands a field the entire page transcript. The
  four text symbols became the whole CV, the number and date symbols became null, and all 44
  cases escalated. The discovery prompt never documented `extraction.labels` or
  `extraction.source` at all, so the agent read "text" as "read it from the text". The prompt
  now explains both, and `ready` refuses a symbol that reads the whole transcript while
  declaring labels or while typed as anything but text: it can only ever be the entire page
  or null.

Two more were bugs in the driver, not in the platform. Publishing refuses a name a process
already has, which is right — a second discovery for an existing process is a version draft —
but the refusal arrived after fifteen minutes of questions and a four-minute compilation, so
`discover` now checks the name before it starts anything. And the comparison read the answer
key's `INTERVIEW` against the engine's `interview` and reported 0 of 44 while every category
was in fact correct; it case-folds now.


## What the agents did, in the report

Every stage of the driver also prints the backend's own audit trail (ADR 0018), so the run
can be inspected rather than trusted: one row per model call with the agent, the model that
answered, requests, rejected outputs, tokens, latency and the trace id, plus fallbacks taken
and validator rejections; and for the batch, each step with its count, time and failures.
`GET /traces/{trace_id}` returns any of those trees in full, including the exact
instructions and output of each call. The dated report of each run holds those tables.

## What is checked without a model

`make check` covers what does not need an LLM:

- `backend/tests/hiring/`: the committed data is exactly what the generator writes, and the
  answer key follows the policy as code.
- `backend/app/features/ingestion/tests/test_hiring_cvs.py`: the generic reader, given the
  schema `manager-notes.md` describes, reads every symbol of the 42 text CVs exactly, Spanish
  labels included, and reads nothing from the 2 scanned ones without OCR. That is the floor
  discovery builds on.

The discovery, compilation, extraction with OCR and learning steps need the agents and are
covered only by the evaluation report of a real run.
