# Criminal-records ERP simulator

This synthetic legacy service is evidence for the hiring discovery demo. It exposes a
complete criminal-record snapshot through the same protocol family as the invoice ERP. It
does not define a hiring source, rule or outcome by itself.

Run it with:

```bash
python3 processes/hiring-screening/criminal_records_erp.py
```

The default address is `http://127.0.0.1:8010`. Use `--port` to choose another port.

## Records

`GET /criminal/records?page=1` returns ISO-8859-1 XML with:

- records at `records/record`;
- total rows at `meta/total`;
- total pages at `meta/pages`;
- fields `id`, `name`, `conviction_date`, `offense` and `status`.

`GET /criminal/status` is unauthenticated and reports `records` and `system`.

The simulator has no authentication and returns every valid request consistently.

All data is fictional. One exact name, `Ana Molina`, also appears in the hiring CV fixture.
That overlap is intentional. A name alone is not a safe real-world identity key, so the
future process change must expose and resolve that limitation during manager review.
