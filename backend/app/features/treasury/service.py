"""Deterministic, read-only payment planning over immutable decision evidence."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.alerts.model import Alert
from app.features.decisions import service as decision_service
from app.features.decisions.model import ENGINE, Decision, DecisionReview
from app.features.ingestion.model import Instance
from app.features.processes.service import get as get_process
from app.features.sources import service as source_service
from app.features.sources.model import Source
from app.features.treasury.config import INVOICE_PAYMENT, InvoicePaymentTreasuryConfig
from app.features.treasury.schemas import (
    TreasuryExclusion,
    TreasuryPlanIn,
    TreasuryPlanOut,
    TreasuryProvenance,
    TreasuryRow,
    TreasurySupplier,
    TreasuryTotals,
    TreasuryWeek,
)
from app.features.versions.model import Execution

CENT = Decimal("0.01")


@dataclass
class _Evidence:
    symbols: dict[str, Any]
    tables: dict[str, list[dict[str, Any]]]
    source_ids: list[int]
    execution_id: int | None
    version_id: int | None
    rules_hash: str
    stale: str | None = None


@dataclass
class _Candidate:
    instance: Instance
    decision: Decision
    evidence: _Evidence
    vendor: str
    amount: Decimal
    currency: str
    currency_source: str
    due_date: date
    due_date_source: str
    amount_source: str
    vendor_source: str


def _cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _flatten(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if not snapshot:
        return {}
    return {
        name: value["value"] if isinstance(value, dict) and "value" in value else value
        for name, value in snapshot.items()
    }


def _first(symbols: dict[str, Any], names: tuple[str, ...]) -> tuple[Any, str | None]:
    for name in names:
        if name in symbols and _text(symbols[name]) is not None:
            return symbols[name], name
    return None, None


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        text = str(value).strip().replace(" ", "")
        if "," in text and "." not in text:
            text = text.replace(",", ".")
        parsed = Decimal(text)
        if not parsed.is_finite():
            return None
        return _cents(parsed)
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value: Any) -> date | None:
    text = _text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _normalize_key(value: Any) -> str:
    return "".join(str(value or "").upper().split())


def _source_matches(
    tables: dict[str, list[dict[str, Any]]],
    config: InvoicePaymentTreasuryConfig,
    symbols: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    order, _ = _first(symbols, config.order_symbols)
    wanted = _normalize_key(order)
    issuer_nif, _ = _first(symbols, ("issuer_nif", "supplier_tax_id"))
    wanted_nif = _normalize_key(issuer_nif)
    if not wanted and not wanted_nif:
        return []
    return [
        (source_name, row)
        for source_name in config.source_names
        for row in tables.get(source_name, [])
        if (
            source_name == "orders"
            and wanted
            and _normalize_key(row.get("purchase_order") or row.get("order")) == wanted
        )
        or (
            source_name == "suppliers"
            and wanted_nif
            and _normalize_key(row.get("nif") or row.get("supplier_tax_id")) == wanted_nif
        )
    ]


def _vendor(
    symbols: dict[str, Any], tables: dict[str, list[dict[str, Any]]]
) -> tuple[str | None, str | None]:
    value, name = _first(symbols, ("issuer_name", "vendor", "supplier_name"))
    if value is not None:
        return _text(value), f"symbol:{name}"
    nif, _ = _first(symbols, ("issuer_nif", "supplier_tax_id"))
    wanted = _normalize_key(nif)
    for row in tables.get("suppliers", []):
        if wanted and _normalize_key(row.get("nif") or row.get("supplier_tax_id")) == wanted:
            value, name = _first(row, ("company_name", "supplier_name"))
            if value is not None:
                return _text(value), f"source:suppliers.{name}"
    if nif is not None:
        return _text(nif), "symbol:issuer_nif"
    return None, None


def _due_date(
    symbols: dict[str, Any],
    tables: dict[str, list[dict[str, Any]]],
    config: InvoicePaymentTreasuryConfig,
    default_terms: int | None,
) -> tuple[date | None, str, str | None]:
    value, name = _first(symbols, config.due_date_symbols)
    if name:
        parsed = _parse_date(value)
        return parsed, f"symbol:{name}", None if parsed else "The recorded due date is invalid"

    source_rows = _source_matches(tables, config, symbols)
    for source_name, source_row in source_rows:
        dates = [
            (_parse_date(source_row.get(field)), field)
            for field in config.due_date_source_fields
            if _parse_date(source_row.get(field)) is not None
        ]
        if dates:
            if len({item[0] for item in dates}) != 1:
                return (
                    None,
                    f"source:{source_name}",
                    "Recorded source fields disagree on the due date",
                )
            return dates[0][0], f"source:{source_name}.{dates[0][1]}", None
    for source_name, source_row in source_rows:
        for field in config.terms_source_fields:
            raw = source_row.get(field)
            if raw is None or _text(raw) is None:
                continue
            try:
                terms = Decimal(str(raw).replace(",", "."))
                if terms != terms.to_integral_value() or terms < 0:
                    raise ValueError
                issue, _ = _first(symbols, config.issue_date_symbols)
                issue_date = _parse_date(issue)
                if issue_date is None:
                    return (
                        None,
                        f"source:{source_name}.{field}",
                        "Recorded payment terms need a valid issue date",
                    )
                return (
                    issue_date + timedelta(days=int(terms)),
                    f"source:{source_name}.{field}",
                    None,
                )
            except (InvalidOperation, OverflowError, ValueError):
                return None, f"source:{source_name}.{field}", "Recorded payment terms are invalid"

    if default_terms is not None:
        issue, _ = _first(symbols, config.issue_date_symbols)
        issue_date = _parse_date(issue)
        if issue_date is None:
            return (
                None,
                "scenario:default_payment_terms_days",
                "The recorded issue date is missing or invalid",
            )
        try:
            return (
                issue_date + timedelta(days=default_terms),
                "scenario:default_payment_terms_days",
                None,
            )
        except OverflowError:
            return (
                None,
                "scenario:default_payment_terms_days",
                "The scenario payment terms exceed the supported date range",
            )
    return None, "missing", "No explicit due date or recorded payment terms were found"


async def _evidence(
    session: AsyncSession,
    instance: Instance,
    decision: Decision | None,
    active_version_id: int | None = None,
    cache: dict[str, Any] | None = None,
) -> _Evidence:
    if decision is None or decision.execution_id is None:
        return _Evidence(
            symbols={},
            tables={},
            source_ids=[],
            execution_id=None,
            version_id=decision.version_id if decision else None,
            rules_hash=decision.rules_hash if decision else "",
            stale="Decision execution snapshot is missing",
        )
    execution = (
        cache.get("executions", {}).get(decision.execution_id)
        if cache is not None
        else await session.get(Execution, decision.execution_id)
    )
    if execution is None:
        return _Evidence(
            {},
            {},
            [],
            decision.execution_id,
            decision.version_id,
            decision.rules_hash,
            "Execution snapshot is missing",
        )
    snapshot_instance = next(
        (item for item in execution.inputs.get("instances", []) if item.get("id") == instance.id),
        None,
    )
    source_ids = [int(item) for item in execution.inputs.get("source_ids", [])]
    if execution.version_id != decision.version_id:
        return _Evidence(
            {},
            {},
            source_ids,
            execution.id,
            decision.version_id,
            decision.rules_hash,
            "Decision version does not match its execution snapshot",
        )
    if active_version_id is not None and execution.version_id != active_version_id:
        return _Evidence(
            {},
            {},
            source_ids,
            execution.id,
            decision.version_id,
            decision.rules_hash,
            "The decision uses a version that is no longer active",
        )
    if execution.inputs.get("down"):
        return _Evidence(
            {},
            {},
            source_ids,
            execution.id,
            decision.version_id,
            decision.rules_hash,
            "The decision run recorded unavailable source data",
        )
    if snapshot_instance is None:
        return _Evidence(
            {},
            {},
            source_ids,
            execution.id,
            decision.version_id,
            decision.rules_hash,
            "Execution instance snapshot is missing",
        )
    if (
        snapshot_instance.get("file_hash") != instance.file_hash
        or snapshot_instance.get("symbols") != instance.symbols
    ):
        return _Evidence(
            {},
            {},
            source_ids,
            execution.id,
            decision.version_id,
            decision.rules_hash,
            "Current instance evidence differs from the recorded decision snapshot",
        )
    loads = (
        (
            [
                cache["sources"][source_id]
                for source_id in source_ids
                if source_id in cache["sources"]
            ]
            if cache is not None
            else list(await session.scalars(select(Source).where(Source.id.in_(source_ids))))
        )
        if source_ids
        else []
    )
    if len(loads) != len(set(source_ids)):
        return _Evidence(
            {},
            {},
            source_ids,
            execution.id,
            decision.version_id,
            decision.rules_hash,
            "Execution source snapshot is missing",
        )
    current = (
        cache["current"]
        if cache is not None
        else {
            load.name: load
            for load in await session.scalars(
                select(Source).where(Source.process_id == instance.process_id).order_by(Source.id)
            )
        }
    )
    captured = {load.name: load for load in loads}
    if set(captured) != set(current):
        return _Evidence(
            {},
            {},
            source_ids,
            execution.id,
            decision.version_id,
            decision.rules_hash,
            "The current source set differs from the captured decision snapshot",
        )
    if any(
        name not in current or current[name].rows != load.rows for name, load in captured.items()
    ):
        return _Evidence(
            {},
            {},
            source_ids,
            execution.id,
            decision.version_id,
            decision.rules_hash,
            "A current source differs from the captured decision snapshot",
        )
    sync = (
        cache["sync"]
        if cache is not None
        else await source_service.sync_status(session, instance.process_id)
    )
    if any(
        (event := sync.get((instance.process_id, load.name))) is not None
        and event.status == "error"
        for load in captured.values()
    ):
        return _Evidence(
            {},
            {},
            source_ids,
            execution.id,
            decision.version_id,
            decision.rules_hash,
            "A source used by the decision is currently unavailable",
        )
    return _Evidence(
        symbols=_flatten((snapshot_instance or {}).get("symbols")),
        tables={load.name: load.rows for load in loads},
        source_ids=source_ids,
        execution_id=execution.id,
        version_id=decision.version_id,
        rules_hash=decision.rules_hash,
        stale=None,
    )


async def _decision_policy(
    session: AsyncSession, process_id: int
) -> tuple[list[tuple[Instance, Decision | None, Decision | None]], set[int]]:
    instances = list(
        await session.scalars(
            select(Instance).where(Instance.process_id == process_id).order_by(Instance.id)
        )
    )
    if not instances:
        return [], set()
    rows = list(
        await session.scalars(
            select(Decision)
            .where(Decision.instance_id.in_([i.id for i in instances]))
            .order_by(Decision.id)
        )
    )
    engines: dict[int, Decision] = {}
    humans: dict[int, Decision] = {}
    for row in rows:
        (engines if row.author == ENGINE else humans)[row.instance_id] = row
    reviews = {
        row.decision_id: row
        for row in await session.scalars(
            select(DecisionReview).where(
                DecisionReview.decision_id.in_([d.id for d in engines.values()])
            )
        )
    }
    historical_human = await decision_service.historical_human_types(
        session, process_id, list(engines.values())
    )
    selected: list[tuple[Instance, Decision | None, Decision | None]] = []
    pending: set[int] = set()
    for instance in instances:
        engine, human = engines.get(instance.id), humans.get(instance.id)
        review = reviews.get(engine.id) if engine else None
        if (
            engine
            and (
                (review and review.requires_human)
                or engine.decision in historical_human.get(engine.id, set())
            )
            and not (human and human.id > engine.id)
        ):
            pending.add(instance.id)
            selected.append((instance, None, engine))
        elif human and (engine is None or human.id > engine.id):
            selected.append((instance, human, engine))
        else:
            selected.append((instance, engine, engine))
    return selected, pending


async def plan(
    session: AsyncSession,
    process_id: int,
    body: TreasuryPlanIn,
    config: InvoicePaymentTreasuryConfig = INVOICE_PAYMENT,
) -> TreasuryPlanOut:
    process = await get_process(session, process_id)
    policy, pending_reviews = await _decision_policy(session, process_id)
    execution_ids = {
        decision.execution_id
        for _instance, decision, _engine in policy
        if decision is not None and decision.execution_id is not None
    }
    executions = (
        {
            row.id: row
            for row in await session.scalars(
                select(Execution).where(Execution.id.in_(execution_ids))
            )
        }
        if execution_ids
        else {}
    )
    source_ids = {
        int(source_id)
        for execution in executions.values()
        for source_id in execution.inputs.get("source_ids", [])
    }
    sources_by_id = (
        {
            row.id: row
            for row in await session.scalars(select(Source).where(Source.id.in_(source_ids)))
        }
        if source_ids
        else {}
    )
    cache = {
        "executions": executions,
        "sources": sources_by_id,
        "current": {
            row.name: row for row in await source_service.current_loads(session, process_id)
        },
        "sync": await source_service.sync_status(session, process_id),
    }
    decision_ids = {decision.id for _instance, decision, _engine in policy if decision is not None}
    unresolved_alerts = (
        set(
            await session.scalars(
                select(Alert.decision_id).where(
                    Alert.decision_id.in_(decision_ids),
                    Alert.status.in_(("open", "acknowledged")),
                )
            )
        )
        if decision_ids
        else set()
    )
    exclusions: list[TreasuryExclusion] = []
    candidates: list[_Candidate] = []
    for instance, decision, engine in policy:
        if instance.id in pending_reviews:
            exclusions.append(
                TreasuryExclusion(
                    instance_id=instance.id,
                    name=instance.name,
                    decision_id=engine.id if engine else None,
                    reason_code="pending_review",
                    reason="The current export policy is waiting for human review",
                )
            )
            continue
        if decision is None:
            exclusions.append(
                TreasuryExclusion(
                    instance_id=instance.id,
                    name=instance.name,
                    reason_code="pending",
                    reason="The instance has no final decision",
                )
            )
            continue
        if decision.decision not in config.eligible_outcomes:
            exclusions.append(
                TreasuryExclusion(
                    instance_id=instance.id,
                    name=instance.name,
                    decision_id=decision.id,
                    reason_code="outcome_not_eligible",
                    reason=(
                        f"Current final outcome {decision.decision!r} is not an approved "
                        "payable outcome"
                    ),
                )
            )
            continue
        if decision.id in unresolved_alerts:
            exclusions.append(
                TreasuryExclusion(
                    instance_id=instance.id,
                    name=instance.name,
                    decision_id=decision.id,
                    reason_code="stale",
                    reason="The current decision has an unresolved data or rule alert",
                )
            )
            continue
        evidence = await _evidence(
            session,
            instance,
            decision,
            getattr(process, "active_version_id", None),
            cache,
        )
        if evidence.stale:
            exclusions.append(
                TreasuryExclusion(
                    instance_id=instance.id,
                    name=instance.name,
                    decision_id=decision.id,
                    reason_code="stale",
                    reason=evidence.stale,
                )
            )
            continue
        amount_value, amount_name = _first(evidence.symbols, config.amount_symbols)
        amount = _parse_decimal(amount_value)
        vendor, vendor_source = _vendor(evidence.symbols, evidence.tables)
        if amount is None or vendor is None:
            missing = [
                name for name, value in (("amount", amount), ("vendor", vendor)) if value is None
            ]
            exclusions.append(
                TreasuryExclusion(
                    instance_id=instance.id,
                    name=instance.name,
                    decision_id=decision.id,
                    reason_code="missing_data",
                    reason=f"Recorded evidence is missing {', '.join(missing)}",
                    details={"fields": missing},
                )
            )
            continue
        if amount <= 0:
            exclusions.append(
                TreasuryExclusion(
                    instance_id=instance.id,
                    name=instance.name,
                    decision_id=decision.id,
                    reason_code="unpayable_amount",
                    reason="The recorded payable amount must be positive",
                    amount=amount,
                    details={"field": amount_name},
                )
            )
            continue
        raw_currency, currency_name = _first(evidence.symbols, config.currency_symbols)
        currency = (_text(raw_currency) or "EUR").upper()
        currency_source = (
            f"symbol:{currency_name}" if currency_name else "invoice-policy-default:EUR"
        )
        if currency in {"€", "EURO"}:
            currency = "EUR"
        if currency != "EUR":
            exclusions.append(
                TreasuryExclusion(
                    instance_id=instance.id,
                    name=instance.name,
                    decision_id=decision.id,
                    reason_code="currency",
                    reason=f"Currency {currency!r} has no adopted conversion policy",
                    amount=amount,
                    currency=currency,
                    details={"currency_source": currency_source},
                )
            )
            continue
        due, due_source, due_error = _due_date(
            evidence.symbols, evidence.tables, config, body.default_payment_terms_days
        )
        if due is None:
            exclusions.append(
                TreasuryExclusion(
                    instance_id=instance.id,
                    name=instance.name,
                    decision_id=decision.id,
                    reason_code="missing_data",
                    reason=due_error or "The due date is not recorded",
                    amount=amount,
                    currency=currency,
                    details={"due_date_source": due_source},
                )
            )
            continue
        candidates.append(
            _Candidate(
                instance,
                decision,
                evidence,
                vendor,
                amount,
                currency,
                currency_source,
                due,
                due_source,
                f"symbol:{amount_name}",
                vendor_source or "missing",
            )
        )

    candidates.sort(
        key=lambda item: (
            item.due_date,
            item.vendor.casefold(),
            item.instance.name.casefold(),
            item.instance.id,
            item.decision.id,
        )
    )
    horizon_end = body.as_of + timedelta(days=body.horizon_weeks * 7 - 1)
    weekly_totals = [Decimal("0.00") for _ in range(body.horizon_weeks)]
    weekly_rows: list[list[TreasuryRow]] = [[] for _ in range(body.horizon_weeks)]
    scheduled: dict[int, TreasuryRow] = {}
    backlog: list[_Candidate] = []
    for item in candidates:
        if item.amount > body.weekly_budget:
            exclusions.append(
                TreasuryExclusion(
                    instance_id=item.instance.id,
                    name=item.instance.name,
                    decision_id=item.decision.id,
                    reason_code="unpayable_amount",
                    reason="The invoice exceeds the weekly budget and cannot be split",
                    amount=item.amount,
                    currency=item.currency,
                    due_date=item.due_date,
                )
            )
            backlog.append(item)
            continue
        if item.due_date > horizon_end:
            exclusions.append(
                TreasuryExclusion(
                    instance_id=item.instance.id,
                    name=item.instance.name,
                    decision_id=item.decision.id,
                    reason_code="outside_horizon",
                    reason="The due date falls after the planning horizon",
                    amount=item.amount,
                    currency=item.currency,
                    due_date=item.due_date,
                )
            )
            backlog.append(item)
            continue
        first_week = max(0, (item.due_date - body.as_of).days // 7)
        target = next(
            (
                idx
                for idx in range(first_week, body.horizon_weeks)
                if weekly_totals[idx] + item.amount <= body.weekly_budget
            ),
            None,
        )
        if target is None:
            exclusions.append(
                TreasuryExclusion(
                    instance_id=item.instance.id,
                    name=item.instance.name,
                    decision_id=item.decision.id,
                    reason_code="budget_unavailable",
                    reason=(
                        "No week in the planning horizon has enough remaining budget; "
                        "the invoice is not split"
                    ),
                    amount=item.amount,
                    currency=item.currency,
                    due_date=item.due_date,
                )
            )
            backlog.append(item)
            continue
        row = TreasuryRow(
            row_id=f"instance-{item.instance.id}",
            instance_id=item.instance.id,
            decision_id=item.decision.id,
            name=item.instance.name,
            vendor=item.vendor,
            amount=item.amount,
            currency=item.currency,
            due_date=item.due_date,
            week_index=target,
            week_start=body.as_of + timedelta(days=target * 7),
            provenance=TreasuryProvenance(
                decision_id=item.decision.id,
                decision_author=item.decision.author,
                decision_at=item.decision.created_at,
                execution_id=item.evidence.execution_id,
                version_id=item.evidence.version_id,
                rules_hash=item.evidence.rules_hash,
                source_ids=item.evidence.source_ids,
                amount_source=item.amount_source,
                vendor_source=item.vendor_source,
                due_date_source=item.due_date_source,
                currency_source=item.currency_source,
            ),
        )
        scheduled[item.instance.id] = row
        weekly_totals[target] += item.amount
        weekly_rows[target].append(row)

    rows = sorted(
        scheduled.values(),
        key=lambda row: (
            row.week_index,
            row.due_date,
            row.vendor.casefold(),
            row.name.casefold(),
            row.instance_id,
        ),
    )
    scheduled_ids = set(scheduled)
    weeks = []
    for idx in range(body.horizon_weeks):
        start = body.as_of + timedelta(days=idx * 7)
        end = start + timedelta(days=6)
        due_backlog = [
            item
            for item in candidates
            if item.due_date <= end
            and (
                item.instance.id not in scheduled_ids
                or scheduled[item.instance.id].week_index > idx
            )
        ]
        week_rows = sorted(
            weekly_rows[idx],
            key=lambda row: (
                row.due_date,
                row.vendor.casefold(),
                row.name.casefold(),
                row.instance_id,
            ),
        )
        weeks.append(
            TreasuryWeek(
                index=idx,
                start=start,
                end=end,
                total=_cents(weekly_totals[idx]),
                remaining_budget=_cents(body.weekly_budget - weekly_totals[idx]),
                row_ids=[row.row_id for row in week_rows],
                backlog_count=len(due_backlog),
                backlog_amount=_cents(sum((item.amount for item in due_backlog), Decimal("0"))),
            )
        )

    supplier_rows = []
    for vendor in sorted({item.vendor for item in candidates}, key=str.casefold):
        items = [item for item in candidates if item.vendor == vendor]
        scheduled_items = [item for item in items if item.instance.id in scheduled_ids]
        pending_items = [item for item in items if item.instance.id not in scheduled_ids]
        supplier_rows.append(
            TreasurySupplier(
                vendor=vendor,
                invoice_count=len(items),
                scheduled_count=len(scheduled_items),
                scheduled_amount=_cents(
                    sum((item.amount for item in scheduled_items), Decimal("0"))
                ),
                backlog_count=len(pending_items),
                backlog_amount=_cents(sum((item.amount for item in pending_items), Decimal("0"))),
            )
        )

    excluded_amount = _cents(
        sum(
            (row.amount or Decimal("0") for row in exclusions if row.currency in (None, "EUR")),
            Decimal("0"),
        )
    )
    backlog_amount = _cents(sum((item.amount for item in backlog), Decimal("0")))
    return TreasuryPlanOut(
        process_id=process_id,
        as_of=body.as_of,
        weekly_budget=_cents(body.weekly_budget),
        horizon_weeks=body.horizon_weeks,
        currency="EUR",
        rows=rows,
        weeks=weeks,
        suppliers=supplier_rows,
        exclusions=exclusions,
        totals=TreasuryTotals(
            scheduled_count=len(rows),
            scheduled_amount=_cents(sum((row.amount for row in rows), Decimal("0"))),
            backlog_count=len(backlog),
            backlog_amount=backlog_amount,
            excluded_count=len(exclusions),
            excluded_amount=excluded_amount,
        ),
    )
