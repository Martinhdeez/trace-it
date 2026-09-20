# Delivery trace links

Each `trace_url` identifies a document by its exact `file_id` within the process.
The console resolves the latest instance with that name, matching export's duplicate-name
policy. Recreating demo instances no longer invalidates these links.

The link opens the current stored case, not an archived execution. A document that has
been removed shows "Documento no encontrado"; it never selects another case silently.
Existing numeric `?i=` links still work while their original instance exists.

The 500-line `outcomes.jsonl` and 40-line `outcomes_lote2.jsonl` keep their original
filenames.

The two files are decided by different process versions, which each line's `rules_hash`
identifies: `outcomes.jsonl` is the rule set frozen on
2026-09-19 for batch 1, which is untouched because a decision already taken is never
rewritten, while `outcomes_lote2.jsonl` is the version published for batch 2, which adds
the currency policy the foreign invoices of that batch made necessary. Each of its lines
carries the whole trace (`export --full`), so the rule that decided, the rate applied and
the arithmetic behind it can be read without opening the console.

Each batch is decided in its own process, as it was for the original delivery, so the
duplicate-order check compares a batch with itself and an invoice is never escalated for
repeating the order of an invoice from the other batch.
