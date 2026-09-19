---
status: accepted
---

# Report incomplete historical coverage when a new schema needs new evidence

## Context

Historical cases were extracted under an earlier published schema. Adding a required
symbol can make them impossible to evaluate under the proposed policy. Treating that
absence as a regression prevents useful schema changes; treating it as a passing case
overstates the available evidence. The runtime requirement must still apply to new cases.

## Alternatives considered

- Block every schema addition until historical PDFs are re-extracted: preserves coverage,
  but couples policy changes to unavailable historical evidence and adds OCR work.
- Make new fields optional or ignore all missing-data errors: permits publication but
  changes the policy and can hide code defects or missing pre-existing requirements.
- Distinguish unavailable historical evidence and validate the new contract with examples:
  permits schema evolution while keeping explicit coverage and existing error gates.

## Decision

1. Compare symbol names in the published and proposed schemas. Only a newly declared
   required field can explain a historical coverage gap. Changing an existing optional
   field to required does not receive this exception.
2. Attempt all rules in the validation sandbox. A validation-only mapping identifies
   actual reads of missing new data, including through other historical instances.
   Keep independent rule results and real execution errors. Do not waive exceptions
   merely because a rule mentions a new field or its final verdict says `MISSING_DATA`.
3. Report incomplete cases as not evaluable with available historical evidence. Do not
   count them as unchanged, changes, review conflicts or successful validation. (R01:
   validation compares with the last engine decision; a person's resolution is reported in
   `resolved_by_person` and never blocks.)
   Preserve blocking failures in rules that can be checked and normal comparisons for
   cases with sufficient evidence. Paired optional reviewer previews use evaluable cases.
4. Return total, evaluated and not-evaluable historical counts, with per-case missing
   symbols and available rule results. Show partial or zero coverage before publication.
   Absence of new historical data alone does not block publication.
5. When a published schema gains required fields, require acceptance examples for each
   new required field both present and absent, even without historical cases. Execute
   them through the proposed policy with all other required fields present. Preserve
   initial bootstrap validation, static code checks, declared-symbol checks and stored tests.
   Missing required values in new cases must still escalate; the runtime engine is unchanged.
6. A case missing an existing required field whose latest decision is already an escalation
   naming those fields (`MISSING_DATA` or `UNVERIFIED_DATA`) followed the policy: report it in
   `already_escalated`, not as an error (2026-09-19, rehearsal 2 blocked on 8 unread scans).
   The same gap on a case decided otherwise stays `MISSING_EXISTING_REQUIRED`.
7. Publish through the existing revision, snapshot and captured-input hash checks. New
   uploads and pending re-extractions use the new schema. Never re-extract historical
   documents automatically or alter earlier decisions and evidence.

## Consequences

A manager can publish a policy with incomplete historical coverage, explicitly reported
as such. Example coverage does not establish correctness for every possible input. Code
after an unavailable data access cannot be validated by that historical run; present-field
examples and stored tests supply additional evidence. Real errors and existing requirements
remain blocking. No LLM is needed to classify the schema change or historical coverage.

## Evidence

- Version validation tests cover new required fields, retained rule results, real errors,
  unknown symbols, existing required fields, proposed examples and coverage counts.
- The ingestion API test publishes an agent-generated rule needing a new required field,
  refreshes a pending document, reads a new document and executes its rule. Another new
  document without the field escalates; earlier decisions and evidence remain unchanged.
- The publication UI presents incomplete coverage separately from blocking validation errors.

## Related

ADRs 0001, 0008, 0016, 0024 and 0029; the
[dynamic extraction guide](../../dynamic-extraction.md#historical-coverage-when-the-schema-grows).
