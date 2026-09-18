"""Evidence-preserving agreement, with correlated-reader and arithmetic safeguards."""

from collections import defaultdict

from app.common.extraction import ExtractedField
from app.features.ingestion.schemas import REQUIRED_INVOICE_FIELDS

from .invoice import arithmetic_checks, parse_invoice
from .uncertainty import preserve_unreadable

POLICY_VERSION = "committee-v1"


def reconcile(readers, min_confidence):
    parsed = {name: parse_invoice(lines, min_confidence)[0] for name, lines in readers.items()}
    fields, decisions, warnings = {}, {}, []
    for name in REQUIRED_INVOICE_FIELDS:
        candidates, votes = [], defaultdict(list)
        statuses = []
        for reader, reading in parsed.items():
            field = reading[name]
            candidates.extend(field.candidates)
            statuses.append(field.status)
            eligible = field.status == "OBSERVED" or (
                reader == "visual" and field.status == "UNVERIFIED"
            )
            if eligible and field.value is not None and not any(c.error for c in field.candidates):
                votes[field.value].append(reader)
        values = {c.value for c in candidates if c.value is not None and c.error is None}
        errors = any(c.error for c in candidates)
        status, value = "MISSING", None
        reason = "no_candidate"
        if candidates:
            status, reason = "UNVERIFIED", "insufficient_independent_support"
            if len(values) > 1 or (values and errors):
                status, reason = "AMBIGUOUS", "conflicting_evidence"
            elif not values and all(s in {"INVALID", "MISSING"} for s in statuses):
                status, reason = "INVALID", "invalid_document_value"
            elif len(values) == 1 and not errors:
                proposed = next(iter(values))
                supporters = votes.get(proposed, [])
                if "native" in supporters or len(supporters) >= 2:
                    status, value, reason = "OBSERVED", proposed, "corroborated"
        fields[name] = ExtractedField(value=value, status=status, candidates=candidates)
        decisions[name] = {"reason": reason, "support": dict(votes)}

    warnings.extend(
        preserve_unreadable(fields, [line for lines in readers.values() for line in lines])
    )
    consistency = arithmetic_checks(fields)
    warnings.extend(consistency)
    if consistency:
        # Clear native values remain observations of an inconsistent document.
        # Matching OCR mistakes are not validated merely by a second local reader.
        for name in ("net_amount", "vat_rate", "vat_amount", "gross_amount"):
            field = fields[name]
            if field.status == "OBSERVED" and not any(
                c.evidence.method == "native" for c in field.candidates
            ):
                field.value, field.status = None, "UNVERIFIED"
                decisions[name]["reason"] = "arithmetic_requires_review"
    for field in fields.values():
        if field.status != "OBSERVED":
            field.value = None
    return fields, decisions, warnings
