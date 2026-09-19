# Criminal-records ERP simulator

This synthetic legacy service is evidence for the hiring discovery demo. It exposes a
complete criminal-record snapshot through the same protocol family as the invoice ERP. It
does not define a hiring source, rule or outcome by itself.

Run it with:

```bash
python3 processes/hiring-screening/criminal_records_erp.py
```

The default address is `http://127.0.0.1:8010`. Use `--port` to choose another port.

## Login

`POST /criminal/login` as an URL-encoded form:

```text
usuario=people
clave=SCREENING2009
```

The XML response contains `token`, `caduca_en_segundos` and `usos_maximos`. Send the token
as `X-Registry-Token` on record requests.

## Records

`GET /criminal/records?page=1` returns ISO-8859-1 XML with:

- records at `records/record`;
- total rows at `meta/total`;
- total pages at `meta/pages`;
- fields `id`, `name`, `conviction_date`, `offense` and `status`.

`GET /criminal/status` is unauthenticated and reports `records` and `system`.

The simulator returns every valid request consistently. Tokens allow 100 record requests;
after that, the service returns `SES-401` and a client can log in again.

All data is fictional. One exact name, `Ana Molina`, also appears in the hiring CV fixture.
That overlap is intentional. A name alone is not a safe real-world identity key, so the
future process change must expose and resolve that limitation during manager review.
