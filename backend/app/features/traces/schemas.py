from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.features.decisions.schemas import DecisionOut


class SpanOut(BaseModel):
    """One step: when it started, how long it took, how it ended and what it saw."""

    id: int
    trace_id: str
    span_id: str
    parent_id: str | None
    step: str = Field(examples=["compile_rule", "llm_run", "run_process", "evaluate_rule"])
    status: str = Field(examples=["ok", "error"])
    started_at: datetime
    duration_ms: int | None  # None for a point event (a decision, a resolution)
    # Step data: tokens (input_tokens, output_tokens), model, config_id, prompt_hash, retries,
    # counts (instances, fired, errors, cases, passed), `error` when it failed.
    data: dict[str, Any] | None
    instance_id: int | None
    process_id: int | None
    rule_id: int | None
    norm_rule_id: int | None


class SpanNode(SpanOut):
    children: list["SpanNode"] = []


class FileOut(BaseModel):
    hash: str
    name: str
    size_bytes: int
    ingested_at: datetime


class RuleResultOut(BaseModel):
    """One rule's answer on the instance, with the rule and the norm sentence it checks."""

    rule_id: int
    hash: str | None
    fires: bool | None  # None: the rule could not be evaluated
    reason: str
    rule_text: str | None
    rule_summary: str | None
    norm_rule_id: int | None


class DecisionTrace(DecisionOut):
    rule_results: list[RuleResultOut]


class SourceRead(BaseModel):
    """The latest `sync_source` span of one source before the instance's latest decision."""

    source: str
    status: str = Field(examples=["ok", "error"])
    started_at: datetime
    duration_ms: int | None
    requests: int
    retries: int
    rate_limited: int  # 429 responses
    timeouts: int
    trace_id: str  # `GET /traces/{trace_id}`: the sync's tree


class InstanceTrace(BaseModel):
    """The journey of one instance: its file, how it was read, its symbols, every decision
    with each rule's answer, what people did, and what the export writes for it."""

    id: int
    process_id: int
    name: str
    status: str
    file: FileOut | None
    symbols: dict[str, Any] | None  # {name: {"value", "origin"}}
    decisions: list[DecisionTrace]  # oldest first; the engine's and people's
    exported_decision: str | None  # what `GET /processes/{id}/export` writes (ADR 0016)
    spans: list[SpanNode]  # ingestion, runs (with per-rule spans), resolutions, exports
    sources_read: list[SourceRead] = []  # by source name; empty before any decision


class RuleRuntime(BaseModel):
    """The rule's code in process runs: `evaluate_rule` spans under `run_process`."""

    runs: int  # completed runs; refused ones are `run_process` errors in `steps`
    instances: int
    fired: int
    errors: int
    p50_ms: float | None
    p95_ms: float | None


class RuleTrace(BaseModel):
    """How a rule was produced and how it behaves."""

    id: int
    process_id: int
    text: str
    status: str
    norm_rule_id: int | None
    norm_rule_text: str | None
    activation: dict[str, Any] | None  # the impact gate's verdict (`report.activation`)
    normalization: SpanOut | None  # the normalizer run that wrote it, if it came from a norm
    compilations: list[SpanNode]  # newest first: tester, coder attempts, tests, reviews
    # Oldest first: saved, (re)compiled, activated, retired, impact previews; who and when
    lifecycle: list[SpanOut]
    runtime: RuleRuntime


class StepStats(BaseModel):
    step: str
    count: int
    errors: int
    p50_ms: float | None
    p95_ms: float | None
    traces: str | None = None  # `GET /traces?...`: the spans behind this row


class LlmStats(BaseModel):
    model: str | None
    role: str | None
    calls: int
    errors: int
    retries: int
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0  # input tokens served from the provider's prompt cache
    requests: int = 0  # model requests, retries and fallbacks included
    fallbacks: int = 0  # calls answered by a later model of the chain (ADR 0019)
    truncations: int = 0  # calls where a model hit its output-token limit
    known_cost_usd: float = 0  # runs whose model has a price (`cost_status` known/included)
    unpriced_requests: int = 0  # model requests of runs with no price: never read as 0 USD
    traces: str | None = None  # `GET /traces?...`: the spans behind this row


class ProviderStats(BaseModel):
    """Provider journal activity; tokens count only attempted network requests."""

    provider: str | None
    model: str | None
    operation: str | None
    attempts: int  # provider_call spans, including journal replays and blocked calls
    network_requests: int
    replays: int  # completed journal reads; blocked uncertain reads remain errors
    errors: int
    input_tokens: int
    output_tokens: int
    blocked: int = 0
    fallbacks: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    network_latency_ms: int = 0
    network_p50_ms: float | None = None
    network_p95_ms: float | None = None
    known_cost_usd: float = 0
    priced_requests: int = 0
    included_requests: int = 0
    unpriced_requests: int = 0
    rate_limited: int = 0  # calls the provider refused with HTTP 429
    traces: str | None = None  # `GET /traces?...`: the spans behind this row


class SourceStats(BaseModel):
    """`sync_source` spans of one source of truth, with its connector's stats."""

    source: str | None
    syncs: int
    errors: int
    requests: int
    retries: int
    rate_limited: int  # 429 responses
    p95_ms: float | None
    traces: str | None = None  # `GET /traces?...`: the spans behind this row


class ProcessMetrics(BaseModel):
    since: datetime | None
    runs: int  # completed runs; refused ones are `run_process` errors in `steps`
    instances_decided: int  # by the engine, in those runs
    instances_per_second: float | None
    steps: list[StepStats]  # every step type: rule compilations, LLM runs, rules, syncs...
    llm: list[LlmStats]  # by model and role
    providers: list[ProviderStats]  # by provider, model and operation
    # Each instance's latest decision, the engine's or a person's.
    decisions_by_outcome: dict[str, int] = Field(examples=[{"PAGAR": 433, "ESCALAR": 31}])
    # Decisions that escalated because a required symbol was missing, a rule failed, needed
    # data or tied.
    failures: dict[str, int] = Field(examples=[{"MISSING_DATA": 29, "RULE_ERROR": 0}])
    escalated: int  # instances whose latest decision waits for a person
    # The escalated instances by their first reason code (`OTHER` if none); adds up to it.
    escalation_reasons: dict[str, int] = Field(examples=[{"MISSING_DATA": 20, "OTHER": 1}])
    pending: int  # instances not decided yet


class Plane(StrEnum):
    """What a span belongs to: reading documents and sources, agents writing rule code, or
    running that code and the people who act on its decisions (`service.PLANES`)."""

    ingestion = "ingestion"
    agents = "agents"
    execution = "execution"


class PlaneMetrics(BaseModel):
    plane: Plane
    process_id: int | None  # None: every process
    since: datetime | None
    spans: int
    errors: int
    steps: list[StepStats]  # the plane's step types only


class IngestionMetrics(PlaneMetrics):
    """Tokens and USD cost per provider in `providers`; no LLM run of the agents counts."""

    files: int  # documents read into instances (`ingest_document`, `extract_document`)
    files_per_second: float | None  # from the first reading's start to the last one's end
    pages: int  # read by the native text layer
    ocr_calls: int
    vision_calls: int
    judge_calls: int
    focused_reads: int
    providers: list[ProviderStats]  # journal attempts and actual network usage by provider
    cache_hits: int  # extractions answered from the extraction cache
    # Declared symbols a reading left null: extraction abstained instead of guessing.
    abstentions: int
    abstentions_by_field: dict[str, int] = Field(examples=[{"iban": 12, "date": 3}])
    sources: list[SourceStats]  # syncs of the sources of truth, by source


class TokenStats(BaseModel):
    """LLM calls grouped by one key: a model, a role, a rule, a norm rule or a use case."""

    key: str | None
    calls: int
    errors: int
    retries: int
    requests: int
    fallbacks: int
    truncations: int
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    known_cost_usd: float  # runs whose model has a price (`cost_status` known/included)
    unpriced_requests: int  # model requests of runs with no price: never read as 0 USD
    traces: str | None = None  # `GET /traces?...`: the spans behind this row


class TokenBucket(BaseModel):
    hour: datetime
    calls: int
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    traces: str | None = None  # `GET /traces?...`: the spans behind this row


class CompileStats(BaseModel):
    compilations: int  # `compile_rule` spans
    valid: int  # ended with code that passed its tests
    success_rate: float | None
    attempts: int  # `coder_attempt` spans
    attempts_per_compilation: float | None
    max_attempts: int  # the most coder attempts one compilation took


class NormStats(BaseModel):
    """One norm submitted: what its agents spent, and when its rules went live."""

    trace_id: str
    started_at: datetime
    author: str | None
    calls: int
    input_tokens: int
    output_tokens: int
    rules_activated: int
    seconds_to_active: float | None  # norm submitted -> its last rule activated
    traces: str  # `GET /traces/{trace_id}`: the norm's whole tree


class AgentsMetrics(PlaneMetrics):
    total: TokenStats  # every LLM run of the plane (`key` None)
    llm: list[LlmStats]  # by model and role
    by_model: list[TokenStats]
    by_role: list[TokenStats]
    by_rule: list[TokenStats]
    by_norm_rule: list[TokenStats]
    by_use_case: list[TokenStats]
    per_hour: list[TokenBucket]
    compile: CompileStats
    norms: list[NormStats]  # newest first


class RuleRunStats(BaseModel):
    rule_id: int | None
    evaluations: int  # `evaluate_rule` spans: one per rule per run
    instances: int
    fired: int
    errors: int
    p50_ms: float | None
    p95_ms: float | None
    traces: str | None = None  # `GET /traces?...`: the spans behind this row


class ExecutionMetrics(PlaneMetrics):
    """The engine never calls a model (ADR 0002): this plane spends 0 tokens by design."""

    runs: int
    instances_decided: int
    instances_per_second: float | None
    rules: list[RuleRunStats]
    decisions_by_outcome: dict[str, int]  # each instance's latest decision
    failures: dict[str, int]  # escalations by cause (MISSING_DATA, RULE_ERROR...)
    escalated: int  # the human queue now
    escalation_reasons: dict[str, int]  # the queue by first reason code (`OTHER` if none)
    pending: int  # instances not decided yet
    resolutions: int  # decisions people took
    resolutions_by_author: dict[str, int]
    resolution_p50_s: float | None  # engine decision -> the person's decision after it
    resolution_p95_s: float | None
    open_alerts: int  # stale decisions nobody acknowledged or acted on (ADR 0026)


class PlaneHealth(BaseModel):
    plane: Plane
    status: str = Field(examples=["ok", "degraded", "down"])
    spans: int
    errors: int
    error_rate: float | None
    p95_ms: float | None
    reason: str | None  # why it is not ok
