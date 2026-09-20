# Delivery trace links

Each `trace_url` identifies a document by its exact `file_id` within the process.
The console resolves the latest instance with that name, matching export's duplicate-name
policy. Recreating demo instances no longer invalidates these links.

The link opens the current stored case, not an archived execution. A document that has
been removed shows "Documento no encontrado"; it never selects another case silently.
Existing numeric `?i=` links still work while their original instance exists.

The 500-line `outcomes.jsonl` and 40-line `outcomes_lote2.jsonl` keep their original
filenames and results. Only their trace URLs have been updated.
