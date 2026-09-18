# trace-it: plan for the agents on PydanticAI

**Status:** execution plan. Documentation only: no code from this plan exists yet.
**Underlying decision:** P23 in `docs/application-blueprint.md`.
**API source:** the local PydanticAI v2 docs in `.context/pydantic-ai/` (see "References"). Every class or function name in this document is checked there. Whatever the docs do not cover is listed in "Unconfirmed APIs".

## 0. Prior decisions (not reopened)

- PydanticAI replaces the direct LiteLLM client (`features/llm/client.py`) in every agent. LangGraph discarded: the state machine, the human queue and idempotency already live in Postgres. No provider lock-in (P22).
- Agents: compilers A and B (blind to each other, P9), escalation assistant, symbol extractor(s) (Álvaro's, on the same infrastructure) and corrector (iteration 2, with tools).
- The LLM never decides in the flow: the engine only runs compiled code (P7).
- Compiler: its `output_validator` runs `sandbox.check` and its **own** tests with `sandbox.run_batch`, and raises `ModelRetry` with the failures. Bounded retries. Cross-tests and the history stay outside the agents, in the pure function `validate`.
- Assistant: its `output_validator` rejects with `ModelRetry` a decision that is not one of the process's types.
- Extraction: the validators (IBAN mod-97, NIF check letter, base + VAT = total), tied to symbol types and not to invoice field names, do **not** raise `ModelRetry`: if they fail, the instance goes to `REVIEW`. Two independent extractions must agree.
- Configuration per role: presets in repo files and versions in the database, editable at runtime, without a restart and without ever losing an experiment (section 4). Prompts versioned in the repo, with an optional override per version. API keys only in `.env`.
- Traceability: every agent run records in `events` the configuration version used (`agent_config.id`), the role, the model that actually answered, the hash of the effective prompt, tokens, cost, latency, retries and result.

## 1. What changes and what does not

| Piece | Today | After |
|---|---|---|
| LLM call | `client.complete(session, role, messages, format)` on top of `litellm.acompletion` | PydanticAI `Agent.run(...)`, with the model built on every call from the role's active version |
| Structured output | JSON validated by hand (`model_validate_json`) | the agent's `output_type=` |
| Repair loop | Our own loop with `assistant`/`user` messages (`MAX_REPAIRS`) | `@agent.output_validator` + `ModelRetry` + `retries={'output': N}` |
| Provider down | 502 error | `FallbackModel` moves to the next model in the chain; if all fail, error and trace |
| Cost | `litellm.completion_cost` | `result.usage.cost` (`Decimal` or `None`, computed with genai-prices) |
| Configuration | `llm_config`: one model per role, overwritten | `agent_config`: versions per role, append-only; presets in `agents/presets/*.json` |
| Tests | `monkeypatch` of `client.complete` | `agent.override(model=FunctionModel(...))` and `models.ALLOW_MODEL_REQUESTS = False` |

Unchanged: `sandbox.py`, the pure function `validate`, the engine, the manager's queue and the contract of `rules.service.compile_rule`.

## 2. Target architecture

### 2.1 File tree

```
backend/app/
  conftest.py                  # models.ALLOW_MODEL_REQUESTS = False for the whole suite
  features/
    llm/                       # generic runtime, unaware of roles or tables
      factory.py               # config dict -> Model (FallbackModel), ModelSettings, UsageLimits
      run.py                   # run(): bounded run + event in `events` + errors
      tests/test_factory.py
      tests/test_run.py
      (client.py, model.py, router.py, schemas.py: deleted in task 8)
    agents/
      model.py                 # AgentConfig (table agent_config), ROLES
      config.py                # active version, create version, activate, presets, export, effective prompt
      schemas.py               # Config, ConfigVersionIn/Out, SuggestionOut
      router.py                # /agents/config..., /agents/presets/..., suggestion
      presets/
        quality.json           # default preset (make setup)
        cheap.json
        fast.json
      prompts/
        compiler.md
        assistant.md
        extractor.md           # maintained by Álvaro
        corrector.md           # iteration 2
      compiler.py              # Agent + output_validator (sandbox); validate() unchanged
      assistant.py             # Agent + output_validator (process types)
      corrector.py             # iteration 2: Agent with read-only tools
      sandbox.py               # unchanged
      tests/
    extraction/                # Álvaro
      extractor.py             # extraction Agent on top of features/llm
      validators.py            # pure, per symbol type
      service.py               # two extractions, comparison, REVIEW
      tests/
```

Layers: `llm/` is the runtime and imports nothing from `agents/`; it receives the configuration already resolved. `agents/` stores the configuration and defines the agents. `extraction/` uses `agents.config` (its `model.py`/service, allowed by the guide) and `llm.run`.

Each agent is a module-level `Agent` with no fixed model (`Agent(None, ...)` is allowed if the model is passed on every `run`). Dependencies (`deps_type`) are dataclasses defined in each agent's module, only where needed (assistant and corrector); there is no shared `deps.py` because there is nothing to share.

### 2.2 Configuration flow

```
  REPO (git)                  POSTGRES                        RUNTIME                      TRACE
 +----------------------+    +----------------------------+    +------------------------+    +-------------------------+
 | agents/presets/      | 1  | agent_config               | 3  | on every call:         |    | events, step "agent":   |
 |   *.json             |--->|  (append-only)             |--->|  active version        |--->|  agent_config_id        |
 |   models, settings,  |    |  id, role, version,        |    |  -> FallbackModel      |    |  role, version          |
 |   retries, limit,    |    |  config JSON, prompt?,     |    |  -> ModelSettings      |    |  prompt_hash, model     |
 |   prompt .md         |    |  author, note, created_at, |    |  -> UsageLimits        |    |  tokens, cost           |
 | agents/prompts/*.md  |    |  is_active (1 per role)    |    |  -> prompt + hash      |    |  latency, retries       |
 +----------------------+    +----------------------------+    +------------------------+    +-------------------------+
            ^                    ^            |
            |                  2 | new version / activate (manager, live)
            +------- 4 export ---------------+
```

1. `make setup` (or `POST /agents/presets/{name}/apply`) loads a preset as new versions.
2. At runtime, the manager creates new versions and activates any of them, including an old one (rollback).
3. Every call reads the active version and builds the model: a change applies from the next call on, without a restart.
4. A good experiment is exported as preset JSON and committed to the repo.

### 2.3 Shared infrastructure (`features/llm/`)

**`factory.py`** (sketch; PydanticAI names checked):

```python
from functools import cache
from pydantic_ai import ConcurrencyLimitedModel, ConcurrencyLimiter, ModelSettings, UsageLimits
from pydantic_ai.models import Model, infer_model
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
from pydantic_ai.models.fallback import FallbackModel

@cache  # one limiter per provider, shared by every role
def _limiter(provider: str) -> ConcurrencyLimiter:
    return ConcurrencyLimiter(max_running=settings.llm_concurrency, name=provider)

@cache  # one Model (and its HTTP client) per name, reused
def _model(name: str, cached: bool) -> Model:
    provider, _, model_id = name.partition(":")
    if cached and provider == "anthropic":
        base = AnthropicModel(model_id, settings=AnthropicModelSettings(
            anthropic_cache_instructions=True, anthropic_cache_tool_definitions=True))
    else:
        base = infer_model(name)
    return ConcurrencyLimitedModel(base, limiter=_limiter(provider))

def model(config: dict) -> Model:
    first, *rest = [_model(n, config.get("cache", False)) for n in config["models"]]
    return FallbackModel(first, *rest) if rest else first

def model_settings(config: dict) -> ModelSettings:
    return ModelSettings(**config["settings"])  # temperature, max_tokens, timeout...

def limits(config: dict) -> UsageLimits:
    return UsageLimits(request_limit=config["request_limit"])
```

- Model names use the PydanticAI format, `provider:model` (`anthropic:claude-opus-5`, `openai:gpt-5`, `google:gemini-3-flash-preview`). In v2, `openai:` uses the Responses API; `openai-chat:` forces Chat Completions.
- The cache is keyed by name, not by version: changing the configuration changes which names are requested, so nothing needs invalidating. `Model`s live as long as the process (the provider owns its HTTP client).
- `ConcurrencyLimitedModel` + one `ConcurrencyLimiter` per provider: at most `TRACE_LLM_CONCURRENCY` concurrent requests to each provider (default 8), across all roles. This is what lets us launch the 540 extractions with one `gather` without exceeding rate limits.
- `cache: true` in the config turns on Anthropic prompt caching for the `anthropic:` models in the chain, as a setting of the model itself (the documented way to give different settings to each model of a `FallbackModel`). The other models do not see it.
- `infer_model` checks the provider's environment variables. It is also used to validate a version before storing it.

**`run.py`**: the only way to call an agent.

```python
@dataclass(frozen=True)
class ActiveConfig:          # what `agents.config` resolves for a role
    id: int                  # agent_config.id
    role: str
    version: int
    config: dict             # models, settings, retries, request_limit, prompt
    prompt: str              # effective text: the version's override or the repo file
    prompt_hash: str         # sha256 of the effective text, first 12 characters

async def run(session, agent, active: ActiveConfig, user_input, *, deps=None,
              output_type=None, instance_id=None, data=None) -> AgentRunResult:
    # 1. agent.run(user_input, model=model(c), instructions=active.prompt, deps=deps,
    #              output_type=..., model_settings=model_settings(c), usage_limits=limits(c),
    #              retries={"output": c["retries"]})
    #    inside asyncio.timeout(settings.timeout * request_limit)
    # 2. record(session, "agent", ...) with the result or the error
    # 3. PydanticAI errors and TimeoutError -> AgentError (TraceError, 502)
```

- The role's prompt goes in as the `run`'s `instructions=` (the parameter exists on `Agent.run`). The prompt is therefore version data, not code.
- `record` only does `session.add`, with no I/O: two concurrent `run`s on the same session (compilers A and B) do not clash if the active version was read before the `asyncio.gather`, just as `_read` preloads `LLMConfig` today.
- Caught: `AgentRunError` (base of `UnexpectedModelBehavior`, `UsageLimitExceeded`, `ModelAPIError`), `FallbackExceptionGroup` (base `ExceptionGroup`) and `TimeoutError`. Anything else is our bug and propagates.

Event per run (`events.step = "agent"`):

| Field | Where it comes from |
|---|---|
| `data.agent_config_id`, `data.role`, `data.version` | `ActiveConfig` |
| `data.prompt_hash` | hash of the effective prompt |
| `data.model`, `data.provider` | `result.response.model_name`, `result.response.provider_name` (the one that actually answered, after fallback) |
| `data.requests`, `data.input_tokens`, `data.output_tokens` | `result.usage.requests`, `.input_tokens`, `.output_tokens` |
| `data.retries` | number of `RetryPromptPart` in `result.all_messages()` |
| `data.result`, `data.error` | `ok` or `error` with the type and the message (500 characters) |
| `cost` | `result.usage.cost` (`None` if genai-prices does not know the model) |
| `latency_ms`, `instance_id` | measured around the `run`; whatever the caller passes |
| rest of `data` | whatever the caller adds (`rule_id`...) |

Note: in v2 `result.usage` is a property, not a method (`result.usage`, not `result.usage()`).

## 3. Agents

### 3.1 Compilers A and B (Martín)

| | |
|---|---|
| Definition | `compiler = Agent(None, output_type=Proposal, name="compiler")`. A single agent; A and B are two runs with different roles (`compiler_a`, `compiler_b`), each with its own active version, models and history. Neither sees the other's work (P9) |
| `output_type` | Current `Proposal`: `code` + `tests` with `instance_json`/`sources_json`/`others_json` as text. Kept: strict JSON Schema mode does not accept free-form objects |
| `deps_type` | none |
| Instructions | `agents/prompts/compiler.md` (the current `SYSTEM`) or the version's override. The rule context (`_context`) goes in the user message |
| Validator | async `@compiler.output_validator`: `_tests(p)` (fewer than `MIN_TESTS` or invalid JSON → `ModelRetry`) and `await asyncio.to_thread(_own_errors, p.code, tests)`; if it returns text → `ModelRetry(text)` |
| Retries / limits | `retries: 2` (same as the current `MAX_REPAIRS`), `request_limit: 4` |
| Invocation | `compile_rule()` reads both active versions, then `asyncio.gather(run(A), run(B))`, then `asyncio.to_thread(validate, ...)` as today |
| Records | one `agent` event per role (with `rule_id`) and the current `compile_rule` event with `valid` and the `agent_config_id` of A and B. If A and B ended up on the same provider (through fallback), `report.same_provider_warning = true` |
| Failure | `AgentError` after exhausting retries or models → `CompilationError` (502). `rules.service.compile_rule` commits the events before re-raising |
| Tests | `compiler.override(model=FunctionModel(fn))`: 1) correct code on the first try → event with `retries=0`; 2) first code that fails its tests and then a good one → `retries=1` and the retry message contains the failing test; 3) always wrong → `CompilationError`. `validate` keeps its pure tests. `fn` answers by calling the output tool (`info.output_tools[0].name`) |

Why the validator runs in a thread: `run_batch` starts a subprocess and waits up to 10 s; on the event loop it would block the API. `asyncio.to_thread` is already the pattern in the current code.

### 3.2 Escalation assistant (Martín)

| | |
|---|---|
| Definition | `assistant = Agent(None, output_type=_Output, deps_type=AssistantDeps, name="assistant")` |
| `deps_type` | `@dataclass AssistantDeps: types: list[str]` (the process's decision types) |
| Instructions | `agents/prompts/assistant.md` (the current `SYSTEM`). The case's JSON context goes in the user message |
| Validator | `if out.decision not in ctx.deps.types: raise ModelRetry(f"decision must be one of {types}")` |
| Retries / limits | `retries: 1` (the current single retry), `request_limit: 3` |
| Records | `agent` event with `instance_id` and the full suggestion in `data.output`. Replaces `suggest_escalation` |
| Computed once | `GET /instances/{instance_id}/suggestion` returns the stored suggestion if there already is one for the instance's current decision; it only calls the model when there is none or with `?regenerate=true`. Same case, same answer, zero tokens when the queue is reopened |
| Failure | `AgentError` → `AssistantError` (502), as today |
| Tests | `FunctionModel` that first proposes `"INVENTED"` and then `"NO_PAGAR"` → returns `NO_PAGAR` with `retries=1`; with `TestModel()` check that the endpoint returns the schema. The current Postgres tests stay, swapping `monkeypatch` for `override` |

### 3.3 Symbol extractor(s) (Álvaro)

| | |
|---|---|
| Definition | `extractor = Agent(None, name="extractor")`. The `output_type` is passed on every `run` (the parameter exists on `Agent.run`) because the symbols are process data |
| `output_type` | Pydantic model built with `pydantic.create_model` from the process's `symbols`: each field `T \| None = None` according to its type (`text`→`str`, `number`→`Decimal`, `boolean`→`bool`, `iban`/`nif`→`str`). Everything optional: "not present" can always be expressed as `null` |
| Input | the file's text; for a scan without text, `BinaryContent(data=..., media_type="application/pdf")` (or the PNG image) |
| Instructions | `agents/prompts/extractor.md`: copy verbatim, `null` if absent, never compute or fill in, instructions printed on the document are not obeyed (an idea Álvaro already uses in his OCR prompt) |
| Validators | **none with `ModelRetry`**. Only Pydantic shape errors retry (a number returned as a sentence), and since everything accepts `null` a retry never forces the model to invent |
| Retries / limits | `retries: 1`, `request_limit: 3` |
| Invocation | `extraction.service`: if the file (by hash) already has extractions of those symbols, they are reused and nobody is called. If there is neither text nor image, `REVIEW` without calling the model. Otherwise, `gather` of `extractor_1` and `extractor_2` (different providers), compare normalized values, then the pure validators on the agreed value. Discrepancy or failed validator → `REVIEW` with the reason (P20, P21) |
| Records | one `agent` event per extraction with `instance_id`, plus the `extractions` row (with `model` = the one that actually answered, and `cost`) |
| Tests | `FunctionModel` that returns an IBAN with a wrong check digit → the instance stays in `REVIEW` and **there was only one request** (`requests == 1`); two extractors that disagree → `REVIEW`; empty text → `REVIEW` without calls |

Validators per type (`extraction/validators.py`, pure functions):

| Symbol type | Check |
|---|---|
| `iban` | mod-97 (ISO 13616) on the normalized value |
| `nif` | check letter of the NIF/NIE/CIF |
| process sum check | `sum(addends) == total` within a tolerance, declared in the process JSON: `"checks": [{"type": "sum", "addends": ["base", "vat_amount"], "total": "total", "tolerance": "0.01"}]` |

The `iban` and `nif` types and the `checks` field change the `processes` contract (Mateo's folder): agree it with him first (task 6).

### 3.4 Corrector (iteration 2, Martín)

| | |
|---|---|
| Definition | `corrector = Agent(None, output_type=ProposedRule, deps_type=CorrectorDeps, name="corrector")` |
| `deps_type` | in-memory snapshot: active rules, sources, symbol history and validated decisions. No `AsyncSession`: the tools do not touch the database |
| Tools | read-only `@corrector.tool`: `try_code(ctx, code)` runs a draft in the sandbox on the instance and the validated decisions (with `asyncio.to_thread`), `view_rule(ctx, rule_id)`. Sandbox errors → `ModelRetry` in the tool |
| Output | `ProposedRule(text, type, decision, explanation)`; validator same as the assistant's (`decision` among the types). The proposal enters as a draft rule and is compiled by A and B like any other: the corrector never writes active code |
| Limits | `request_limit: 10`; `UsageLimits(tool_calls_limit=...)` can be added to the config if needed |
| Tests | `FunctionModel` that calls `try_code` and then returns the proposal |

## 4. Configuration

### 4.1 Table `agent_config` (replaces `llm_config`)

| Column | Type | Note |
|---|---|---|
| `id` | `bigint` PK | what every event stores |
| `role` | `text` not null | one of `ROLES` |
| `version` | `int` not null | 1, 2, 3... per role; `unique (role, version)` |
| `config` | `jsonb` not null | shape below |
| `prompt` | `text` null | prompt override for experiments; `null` = the repo file |
| `author` | `text` not null | user's email or `preset:<name>` |
| `note` | `text` null | what is being tried |
| `created_at` | `timestamptz` | |
| `is_active` | `bool` not null default false | partial unique index `(role) where is_active`: at most one active per role |

Rules:
- A row is never deleted, and its `config`, `prompt`, `author` or `note` never change. Editing means creating a new version.
- The only write to an existing row is moving `is_active`: deactivate the previous one and activate the new one in the same transaction. Each activation leaves an `activate_agent_config` event (role, from `id`, to `id`, author), so we know what was active and when. (Alternative discarded for having more parts: a separate activations table.)
- Rolling back = activating an old version.
- A role with no active version does not run: `ConflictError` "role X has no active configuration: run make setup".

Shape of `config` (the same as each role in a preset):

```json
{
  "models": ["anthropic:claude-opus-5", "anthropic:claude-sonnet-5"],
  "settings": {"timeout": 120},
  "retries": 2,
  "request_limit": 4,
  "prompt": "compiler.md"
}
```

- `models`: fallback chain, the first one is the primary. At least one.
- `settings`: subset of `ModelSettings` (`temperature`, `max_tokens`, `timeout`, `seed`). `timeout` is required; `temperature` is left out for models that do not accept it (Claude Opus 4.7/4.8/5 reject sampling settings; PydanticAI drops them and warns).
- `retries`: output retry budget (`retries={'output': N}`).
- `request_limit`: `UsageLimits(request_limit=...)`.
- `prompt`: file in `agents/prompts/`.
- `cache` (optional, `false` by default): Anthropic prompt caching on the `anthropic:` models of the chain (7.3).

Validation when creating a version (`schemas.Config`, Pydantic with `extra="forbid"`): each model has a `provider:` prefix and can be built with `infer_model` (if the provider key is missing, 422); `retries` between 0 and 5; `request_limit` between 1 and 20; `timeout` between 5 and 600; the prompt file exists.

### 4.2 Presets

`backend/app/features/agents/presets/<name>.json`:

```json
{
  "description": "Highest quality; different providers in each pair",
  "roles": {
    "compiler_a":  {"models": ["anthropic:claude-opus-5", "anthropic:claude-sonnet-5"], "settings": {"timeout": 120}, "retries": 2, "request_limit": 4, "prompt": "compiler.md"},
    "compiler_b":  {"models": ["openai:gpt-5", "google:gemini-3-pro-preview"], "settings": {"timeout": 120}, "retries": 2, "request_limit": 4, "prompt": "compiler.md"},
    "extractor_1": {"models": ["anthropic:claude-sonnet-5", "anthropic:claude-haiku-4-5"], "settings": {"temperature": 0, "timeout": 60}, "retries": 1, "request_limit": 3, "prompt": "extractor.md", "cache": true},
    "extractor_2": {"models": ["openai:gpt-5-mini", "google:gemini-3-flash-preview"], "settings": {"temperature": 0, "timeout": 60}, "retries": 1, "request_limit": 3, "prompt": "extractor.md"},
    "assistant":   {"models": ["anthropic:claude-opus-5", "openai:gpt-5"], "settings": {"timeout": 90}, "retries": 1, "request_limit": 3, "prompt": "assistant.md"}
  }
}
```

| Preset | Idea |
|---|---|
| `quality.json` | the one above, the default. The primary models are those of the initial `llm_config` migration |
| `cheap.json` | small models in every role (Sonnet/Haiku, `gpt-5-mini`, Gemini Flash) |
| `fast.json` | like `cheap` but with a low `timeout` and `retries` 1 |

The chains of each pair (`compiler_a`/`_b`, `extractor_1`/`_2`) do not share a provider, not even in the fallback: a provider outage cannot make A and B, or the two extractions, end up on the same model (P9, P20, P22). The names exist in `KnownModelName` in the local docs; they are checked with `infer_model` when the preset is loaded.

Applying a preset (`agents.config.apply_preset`), per role: if the active version already has that `config` and no overridden `prompt`, it does nothing; otherwise it creates a version (`author = "preset:<name>"`) and activates it. `make setup` applies `quality` **only to roles with no version at all**: like process definitions, it does not overwrite what was changed at runtime.

### 4.3 Prompts

- By default, `agents/prompts/<file>.md`, versioned with git.
- Effective prompt = `agent_config.prompt` if not `null`; otherwise the file named by `config.prompt`.
- Read on every call (a small file; no cache, so editing the `.md` locally takes effect without a restart).
- Hash: `sha256(effective_text)[:12]`, stored in every event. Two runs with the same hash used exactly the same prompt, whether it came from the file or the database.
- Whatever varies (rule, symbols, case) always goes in the user message, never in the prompt: the prompt is fixed and its hash means something. It also leaves a stable prefix for the providers' implicit caching.

### 4.4 Endpoints

They replace `GET /llm/config` and `PUT /llm/config/{role}` (tell Carlos).

| Method and path | What it does | Who |
|---|---|---|
| `GET /agents/config` | Active version of each role | anyone |
| `GET /agents/{role}/config/versions` | Every version of the role, newest first | anyone |
| `POST /agents/{role}/config` | Body `{config, prompt?, note?, activate=false}`. Creates the next version; `activate` activates it in the same transaction | manager |
| `POST /agents/{role}/config/{config_id}/activate` | Activates that version (including an old one) | manager |
| `POST /agents/presets/{name}/apply` | Applies a preset from the repo (4.2) | manager |
| `GET /agents/{role}/config/{config_id}/export` | Returns `{"roles": {role: config}}`, the preset format, plus `prompt_text` if the version overrides the prompt, to commit the experiment to the repo | anyone |

`author` comes from `CurrentUser` (`X-User-Id`). Errors: unknown role → 404; version of another role → 404; invalid config → 422.

Comparing configurations afterwards is a query over `events`:

```sql
select data->>'agent_config_id' as config, count(*) as calls,
       avg(latency_ms) as ms, sum(cost) as usd,
       avg((data->>'retries')::int) as retries
from events where step = 'agent' and data->>'role' = 'compiler_a'
group by 1;
```

## 5. Sandbox integration

| Where | What is called | How |
|---|---|---|
| Compiler `output_validator` | `sandbox.check(code)` and `sandbox.run_batch(code, own tests)`, via `_own_errors` | `await asyncio.to_thread(...)`; batch timeout 10 s (that of `run_batch`); the failure goes back to the model as `ModelRetry` |
| `validate` (pure, outside the agent) | `run_batch` with all A+B tests and the history, on both codes | `asyncio.to_thread(validate, ..., sandbox.run_batch)` after the `gather`, as today. No retry: the manager resolves a cross failure (P9) |
| Corrector tools (iteration 2) | `run_batch` on the instance and the validated decisions | `asyncio.to_thread` inside the tool; error → `ModelRetry` |
| Engine | `run` / `run_batch` | unchanged, no LLM |

Timing: the validator may run up to `retries + 1` times per compilation, each ≤ 10 s of sandbox, and counts within `run`'s wall-clock limit (`timeout × request_limit`). With the `quality` preset: 120 s × 4 = 8 min as the absolute ceiling per agent; 30-60 s is typical.

## 6. Cost and resilience

**Cost**
- `UsageLimits(request_limit=...)` per role bounds retries and the tool loop. `cost_limit` exists but is "best-effort" according to the docs (it depends on genai-prices knowing the model): it is not used as a guarantee.
- Tiered models: high-volume roles (extraction, ~1,000 calls per batch) use small models; low-volume ones (compiler, assistant) use the large ones. Changed by preset, without touching code.
- Prompt caching: only where the same prefix repeats a lot, that is, in extraction (7.3). For the compiler and the assistant it does not pay off (few calls, 1-2 k token prompts).
- Batch: the local docs do not describe the providers' batch APIs. Not used.
- `service_tier` (`'flex'` on OpenAI) is documented; a possible lever for `cheap.json`, not in v1.
- Prices of new models: `pydantic_ai.prices.update_in_background()` at startup, optional. Without it, `cost` may be `None` for models newer than the installed version.

**Resilience**
- `FallbackModel` moves to the next model on `ModelAPIError` (4xx/5xx). Validation errors do not trigger fallback: they retry with the same model (documented that way).
- `settings.timeout` bounds each request attempt (OpenAI, Anthropic and Google apply it). PydanticAI does not bound the total wall clock of a `run`: `asyncio.timeout` in `run` does.
- The OpenAI and Anthropic SDKs retry 2 times on their own by default, which delays fallback up to 3 × `timeout`. Accepted in v1; if in testing the switch to the next model takes too long, `factory` builds those providers with `max_retries=0` (`AnthropicProvider(anthropic_client=AsyncAnthropic(max_retries=0))`, `OpenAIProvider(openai_client=AsyncOpenAI(max_retries=0))`, documented) by passing `provider_factory` to `infer_model`.
- If every model fails: `FallbackExceptionGroup` → `AgentError` → event with `result = "error"` → the operation fails closed:
  - compile: the rule stays a draft, the previous one stays active, the process does not stop (3.2 of the blueprint);
  - assistant: 502; the manager resolves without a suggestion;
  - extraction: the instance stays in `REVIEW` with reason "model unavailable" and counts in the queue; we never decide without symbols.

## 7. Performance, tokens and determinism

### 7.1 Where tokens are spent

| Stage | When it calls the LLM | Calls | Order of magnitude (estimate; confirmed with 7.4) |
|---|---|---|---|
| Compile | Once per rule change, never per instance | 2 agents × (1 + repairs) | ~5 k tokens per request; the whole v3 policy (~12 rules) ≈ 24-72 requests |
| Engine | Never | 0 | 0 tokens per instance: it runs compiled code |
| Assistant | On demand, per escalated case, and only once per case (3.2) | 1-2 | ~5-15 k tokens per suggestion (it carries the file text) |
| Extraction | Once per file, two readers | 540 files × 2 = ~1,080 | ~2-3 k tokens per text reading: **the stage that dominates cost and time** |

Engine time, measured locally (macOS, one rule's code, `sandbox.run_batch`): 540 cases in ~40 ms in a single subprocess; ~0.27 s if each case carries the other 539 instances in `others`. The cost is in starting the subprocess: `sandbox.run` case by case costs ~20 ms per case. Today `decisions.service.run` calls `sandbox.run` for every instance and rule, inside the event loop: with 540 instances and ~12 rules that is ~6,500 subprocesses, ~2 minutes with the API blocked. Recommendation for Mateo (outside this plan): one `run_batch` per rule over all pending instances, in `asyncio.to_thread`. That would drop to ~12 subprocesses and a few seconds.

### 7.2 Determinism by construction

We do not rely on `temperature=0`: the docs themselves say that "even with `temperature` 0.0 the results will not be fully deterministic" (`pydantic-ai-settings.md`). Determinism comes from computing each LLM artefact once, storing it and never calling again:

| Artefact | Computed | Stored in | Key | Reused by |
|---|---|---|---|---|
| Symbols of a file | once per file and symbol list | `extractions`, `instances.symbols` | file hash (`files.hash`) | engine, audit, recompilations (history), P10 |
| Code of a rule | once per rule text | `rules.code_a/_b`, `tests_a/_b` | `rules.hash` (text + codes) | engine, retroactive audit |
| Assistant suggestion | once per case and current decision | `agent` event (`data.output`) | instance + decision | manager's queue |
| Configuration used | per call | `agent_config` + `events.data.agent_config_id` | `agent_config.id` + `prompt_hash` | comparing experiments |

Consequence: repeating a run or an audit (3.6, 3.7 of the blueprint) reads stored symbols and code and runs the engine, without any LLM. The result is bit-for-bit identical because the inputs are. The only thing that can vary between two compilations of the same text is the generated code, and P9 (A and B must agree) and the manager's review before activation cover that.

### 7.3 Efficient extraction

- **Text before vision.** A PDF with text goes to the model as the `pdftotext` text stored in `files.text` (no image tokens). Only scans (empty `text`) go as `BinaryContent`.
- **Small models for text.** `extractor_1`/`_2` use small models in every preset. If scans need a larger model, add roles `scan_extractor_1`/`_2` with their own chain; not before measuring it.
- **Never extract twice.** Before calling, `extraction.service` looks for extractions of the same file hash with the same symbols. A new symbol (P10) is extracted on its own, from the stored text.
- **Prompt caching (Anthropic).** The prefix that repeats across a reader's ~540 readings is the instructions and the output schema (the output tool with the process's symbols). PydanticAI documents `AnthropicModelSettings.anthropic_cache_instructions` and `anthropic_cache_tool_definitions`, each with one cache point; they are turned on with `"cache": true` in the config (2.3). Whatever varies (the invoice text) goes after, in the user message. OpenAI: the docs only describe caching with `CachePoint` for GPT-5.6 onwards, so we do not count on it for `gpt-5-mini`. Gemini: requires creating the cache resource with Google's SDK outside PydanticAI; not in v1. The effect is measured in `result.usage.cache_read_tokens` (worth adding to the event). The local docs do not give the minimum cacheable prefix size: if the prefix is too short, `cache_read_tokens` comes out 0 and it is switched off.
- **No Batch API**: it is not in the PydanticAI docs.
- **Bounded concurrency.** `extraction.service` launches every reading with `asyncio.gather`; `factory`'s per-provider `ConcurrencyLimiter` lets `TRACE_LLM_CONCURRENCY` through at a time (documented: `ConcurrencyLimitedModel`, `ConcurrencyLimiter(max_running=..., name=...)`). With 8 per provider and ~3 s per reading, 540 files ≈ 540 / 8 × 3 s ≈ 3-4 minutes, with both readers in parallel because they go to different providers. Any 429s that still arrive are retried by the SDK and, if they persist, fall through to the next model.

### 7.4 Budget control

- Per run: `UsageLimits(request_limit=...)` and `retries` of each config version (section 4). A compilation cannot exceed `request_limit` requests per agent, whatever happens.
- Per process: `GET /processes/{process_id}/metrics` (feature `traces`, task 5) aggregates `events`:
  - per stage and role: calls, errors, total cost, tokens, p50 and p95 latency (Postgres `percentile_cont`);
  - cost per instance: extraction and assistant cost / distinct instances;
  - engine: time per run (needs one `engine` event per run in `decisions.service.run`, to agree with Mateo).
- For that, every `agent` event carries `data.process_id` (the caller passes it in `data`).
- The same endpoint gives the demo figures ("0 tokens per decision; X € per extracted invoice; compiling the policy cost Y €") and the ADR evidence (P23).

### 7.5 Option to evaluate, not decided: compiled extractors

The idea: apply to extraction what we do for rules. From the symbol list and a few sample texts of one document format, an agent writes a deterministic parser `extract(text) -> dict`; it is validated like a rule (two agents, tests with the values already agreed by the double LLM extraction of those samples) and runs in the sandbox. At runtime: parser → per-type validators → if anything fails or a symbol is missing, LLM reading as now.

| For | Against |
|---|---|
| 0 tokens and milliseconds per file once the format is compiled | Files must be grouped by format (by issuer NIF or by text fingerprint); with many different formats it pays off little |
| Truly deterministic, and tells the same story as the rules: "everything that decides is compiled code" | Fragile with unseen formats: without the LLM fallback, a template change breaks silently |
| Reuses the sandbox, the compiler and `validate` | Scans still need OCR or vision |
| | P20 discards "per-template parsers"; this only fits because agents generate and validate the parsers, and the blueprint must say so |
| | The test labels come from LLM extraction: it does not remove the LLM, it moves it to compilation |

Effort: ~1 day (format key, `extract` contract, reuse compiler and `validate`, LLM fallback, coverage metrics). A point in favour: Álvaro's `data-ingestion` branch already extracts the 471 native PDFs with a hand-written parser (`ingesta/pdf/invoice.py`) and its audit found no discrepancies in the fields reviewed: the text of these PDFs is regular.

Recommendation: **not before H2.** Batch 1 is closed with the double LLM extraction, which already stores the agreed values. After H2, count distinct formats with that data: if ~20 formats cover more than 90 % of the files, compile extractors for batch 2 and the demo; otherwise it does not pay off.

## 8. Observability

- **Source of truth: `events`.** It is what the application queries, what is exported and what the demo shows ("why was X decided"). It depends on no external service.
- **OpenTelemetry / Logfire: optional, off by default.** PydanticAI emits spans per request and per tool with `Agent.instrument_all()` or `logfire.instrument_pydantic_ai()`; with `logfire.configure(send_to_logfire='if-token-present')` nothing is sent without `LOGFIRE_TOKEN`. It helps debug a compiler that retries oddly, not product traceability. If enabled: `InstrumentationSettings(include_content=False)` so no invoices or system prompts leave. Requires the `logfire` extra (task 9). In v2 the default format is version 5, with aggregated usage in `gen_ai.aggregated_usage.*`.

## 9. Tasks (one per PR, in order)

Package: **`pydantic-ai-slim[openai,anthropic,google]>=2.45,<3`** (2.45.0 is the latest on PyPI as of 2026-09-18; `uv.lock` pins the exact one). `slim` because the full `pydantic-ai` also brings CLI, MCP, evals, web, retries and logfire, which we do not use.

| # | Branch | Who | Files | Done when | Tests |
|---|---|---|---|---|---|
| 1 | `feat/agents-config` | Martín | `pyproject.toml` (add `pydantic-ai-slim`), `agents/model.py`, `agents/config.py`, `agents/schemas.py`, `agents/router.py`, `agents/presets/*.json`, `agents/prompts/*.md` (the current `SYSTEM` prompts), migration `0007` (creates `agent_config`; `llm_config` stays until task 8), `app/cli.py` (`presets apply <name> [--if-missing]`), `Makefile` (`setup` applies `quality --if-missing`), `.env.example` (`GEMINI_API_KEY` → `GOOGLE_API_KEY`, the PydanticAI variable) | The 6 endpoints of 4.4 answer; running `make setup` twice creates no extra versions; activating an old version works; there are never two active | versions and activation against Postgres; partial unique index; idempotent preset; export → apply gives the same config; invalid config → 422 |
| 2 | `feat/llm-run` | Martín | `llm/factory.py`, `llm/run.py`, `app/conftest.py` | `run` records the full event on success and on error | `FunctionModel` with valid output → event with `model`, tokens, `agent_config_id`, `prompt_hash`; `FallbackModel(FunctionModel(fails with ModelAPIError), FunctionModel(ok))` → `model` is the second one; all fail → `AgentError` and `error` event; request limit → error |
| 3 | `feat/compiler-pydantic-ai` | Martín | `agents/compiler.py`, `agents/tests/test_compiler.py`, `rules/service.py` (commit events on failure) | `make compile` compiles policy v3 as before; events carry the version used | 3.1 |
| 4 | `feat/assistant-pydantic-ai` | Martín | `agents/assistant.py`, `agents/tests/test_assistant.py` | `GET /instances/{instance_id}/suggestion` as before, but returns the stored one if it exists | 3.2 |
| 5 | `feat/agent-metrics` | Martín | `traces/service.py`, `traces/router.py`, `traces/schemas.py`, `main.py`; `data.process_id` in events | `GET /processes/{process_id}/metrics` returns 7.4 for the invoice process | synthetic events → correct p50/p95 and cost per instance |
| 6 | `feat/validatable-symbols` | Álvaro with Mateo | `processes/definition.py`, `processes/schemas.py`, `processes/README.md`, `processes/invoice-payment.json` (types `iban`, `nif`; `checks`) | the invoice JSON declares its types and its sum; `travel-expenses.json` still loads | load with and without `checks`; unknown type → rejected |
| 7 | `feat/extraction-agents` | Álvaro | `extraction/extractor.py`, `extraction/validators.py`, `extraction/service.py`, `agents/prompts/extractor.md` | the 500 invoices go through double extraction; no call retries because of a validator; repeating the extraction calls no model (cache by hash) | 3.3, and one test per validator (IBAN, NIF, sum) with good and bad cases |
| 8 | `chore/remove-litellm` | Martín | delete `llm/client.py`, `llm/model.py`, `llm/router.py`, `llm/schemas.py`; `main.py`; migration `0008` (drops `llm_config`); `pyproject.toml` (drop `litellm`); `docs/team-guide.md` | `grep -ri litellm backend` is empty; `make test` green | full suite |
| 9 | `feat/logfire-observability` (optional) | whoever wants it | `logfire` extra, startup conditional on `LOGFIRE_TOKEN` | without a token nothing changes | no new ones |
| 10 | `feat/corrector` (iteration 2) | Martín | `agents/corrector.py`, `agents/prompts/corrector.md`, `corrector` role in the presets | F12 works with proposals that go through A and B | 3.4 |

What Álvaro has to adopt (tasks 6 and 7):
- Build nothing on `client.complete`: it goes away in task 8. His `data-ingestion` branch still declares `litellm` in `pyproject.toml`; when rebasing, do not use it.
- Every LLM call goes through `llm.run` with an `agent_config` role. If the Gemini OCR (`ingesta/ocr/gemini.py`, today direct `httpx` with `GEMINI_API_KEY`) joins the flow, it becomes one more agent (`output_type=str`, `BinaryContent` input) with its own role, so it shows up in the trace and the presets. While it is an experiment outside the flow, it can stay as it is.
- Validators without `ModelRetry` (section 10).

## 10. Risks and what not to do

| Don't | Why |
|---|---|
| Raise `ModelRetry` when an extraction validator fails (IBAN, NIF, sum) | You tell the model "this IBAN does not check out, try again" and the model learns to return an IBAN that checks out, not the one on the invoice. The validator stops catching errors and starts fabricating plausible data. The right output is `REVIEW` |
| Make a field of the extraction output required | A retry for "missing field" pushes the model to fill it in. Everything `T \| None` |
| Pass the `AsyncSession` in `deps` or use it inside validators or tools | A and B run at the same time on the same session; async SQLAlchemy does not allow concurrent operations on one session. `deps` carry data already read |
| Call `agent.run` outside `llm.run` | The trace and the `agent_config_id` are lost; it can no longer be compared |
| Put case data in the prompt | The hash no longer identifies the prompt and the stable prefix breaks |
| Run the `sandbox` on the event loop | Blocks the API for up to 10 s per batch. Always `asyncio.to_thread` |
| Update or delete `agent_config` rows (except moving `is_active`) | Experiments are lost and old events point to a config that is no longer the one that ran |
| Use deferred tools (`requires_approval`), durable execution (Temporal, DBOS, Prefect) or `pydantic_graph` | Human approval already is rule activation and the queue in Postgres; runs last seconds and can be repeated; the flow is already in our code. They would add duplicate state outside the database |
| Use `SpendLimits` (`pydantic_ai_harness`) | It is another package and solves daily budgets shared across processes, which we do not have |
| Trust `cost_limit` as a spending cap | The docs say it is approximate; the real cap is `request_limit` and the provider limits |
| Model names without a prefix (`'gpt-5'`) | In v2 they raise `UserError` |

Risks:
- **Agreement through fallback.** If A's primary provider goes down, A and B could end up in the same family. Mitigated with disjoint chains per pair (4.2) and the warning in the report (3.1).
- **Minor version changes.** PydanticAI's policy allows changing OpenTelemetry attributes and adding fields to messages in minor versions. We depend on none of them: we read `result.usage` and `result.response`.
- **Models that reject settings.** Claude Opus 5 does not accept `temperature`; PydanticAI drops it and warns. That is why the presets do not set it for roles on Opus.

## 11. APIs not confirmed in the local docs

- **That a timeout or a connection error reaches `FallbackModel` as `ModelAPIError`.** The docs say fallback triggers on `ModelAPIError` and that, when `timeout` expires, "the provider client raises"; they do not say whether it is wrapped. Task 2 checks it; if it is not wrapped, `fallback_on` accepts a custom exception handler.
- **Provider settings passed in the `run`'s `model_settings` with a mixed `FallbackModel`** (for example `anthropic_cache_instructions` with an OpenAI model in the chain). Undocumented; that is why caching goes in the settings of the `AnthropicModel` itself (documented in "Per-Model Settings").
- **Whether `anthropic_cache_tool_definitions` covers the output tool** (the one carrying the symbol schema) as well as function tools. The docs talk about "tool definitions" without distinguishing; it shows in `cache_read_tokens`.
- **Minimum prefix size for Anthropic caching to kick in.** Not in the local docs.
- **Whether an output with fallback counts as one or several requests in `request_limit`.** Undocumented; the presets leave one request of margin.
- **Providers' batch APIs.** They do not appear in the PydanticAI docs.
- **`result.usage()`** as a method: in v2 it is the property `result.usage`.

## 12. References

Local PydanticAI docs (`.context/pydantic-ai/sections/`):

| Decision | Section |
|---|---|
| `Agent(...)`, `run(model=, instructions=, output_type=, model_settings=, usage_limits=, retries=)`, `override` | `pydantic-ai-agent.md` (`__init__`, `run`, `override`), `agents.md` |
| `output_validator`, `ModelRetry`, `ToolOutput`, `StructuredDict`, output modes | `output.md` |
| Retry budgets and what is retried | `retries.md`, `agents.md` ("How output retries are enforced") |
| `FallbackModel`, `fallback_on`, per-model settings, `FallbackExceptionGroup` | `model-providers.md` ("Fallback Model"), `pydantic-ai-models-fallback.md`, `pydantic-ai-exceptions.md` |
| `infer_model`, `provider:model` format, HTTP client life cycle | `pydantic-ai-models.md`, `model-providers.md` |
| `ModelSettings` (`temperature`, `timeout`) and who supports them | `pydantic-ai-settings.md`, `timeouts.md` |
| `UsageLimits`, `RunUsage.cost`, prices | `agents.md` ("Usage Limits"), `pydantic-ai-usage.md` |
| `AgentRunResult.response`, `.usage`, `ModelResponse.model_name`, `.provider_name`, `RetryPromptPart` | `pydantic-ai-run.md`, `pydantic-ai-messages.md`, `retries.md` |
| `RunContext`, `deps_type` | `dependencies.md` |
| Corrector tools | `function-tools.md`, `timeouts.md` |
| `BinaryContent` for scans | `multimodal-input.md` |
| Prompt caching | `anthropic.md` ("Prompt Caching", "Cache Point Limits"), `openai.md` ("Prompt caching"), `google.md` ("Context caching") |
| Per-provider concurrency: `ConcurrencyLimitedModel`, `ConcurrencyLimiter` | `model-providers.md` ("HTTP Request Concurrency"), `pydantic-ai-concurrency.md` |
| `temperature` 0 is not deterministic; which models reject sampling settings | `pydantic-ai-settings.md`, `pydantic-ai-profiles.md` (`anthropic_disallows_sampling_settings`) |
| SDK retries and `max_retries=0` | `anthropic.md`, `openai.md`, `retries.md` |
| Tests: `TestModel`, `FunctionModel`, `AgentInfo`, `ALLOW_MODEL_REQUESTS` | `unit-testing.md`, `pydantic-ai-models-function.md`, `pydantic-ai-models-test.md` |
| OpenTelemetry, Logfire, `include_content=False` | `pydantic-logfire-debugging-and-monitoring.md` |
| Programmatic hand-off (our pattern) versus delegation and graphs | `multi-agent-applications.md` |
| Why not durable execution | `durable-execution.md` |
| v2 changes (`openai:` = Responses, `ModelProfile` as `TypedDict`, extras) | `upgrade-guide.md`, `v1-v2-migration-map.md`, `version-policy.md` |
| Comparisons (written by Pydantic, with its bias) | `pydantic-ai-vs-langchain-langgraph.md`, `pydantic-ai-vs-crewai.md`, `pydantic-ai-vs-claude-agent-sdk.md`, `pydantic-ai-vs-openai-agents-sdk.md` |

Ideas taken from winning repos (`hackInfo/.context/repos-ganadores/`, `.docs/`). None uses PydanticAI; what we reuse is the design:
- `prosperai-challenge/src/prosper/llm.py`: explicit per-request timeout (15 s) instead of the default 600 s, and a fallback model. → required `settings.timeout` and a fallback chain.
- `prosperai-challenge/tests/test_llm_failure.py`: a test with an LLM that always fails checks that the system degrades without breaking. → "every model fails" test in task 2.
- `prosperai-challenge` `make mock-eval` (deterministic LLM, 5 s, 0 tokens) and `tests/test_prompts.py` (tests over the prompts). → `FunctionModel` in every test and a test that loads every preset and every prompt.
- `.docs/momentos-de-demo.md` C2 "fail closed and loud" and C3 "silence hallucinates". → instances in `REVIEW` when there is no model or no text, without calling the LLM.
- `.docs/tecnicas-ganadoras.md` 5 and 6 ("the LLM off the hot path", "the LLM talks; something else decides"). → already P7; this plan does not change it.
