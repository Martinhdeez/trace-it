# Historical OCR abstention policy

This page records `invoice-v1.8.0+xlsx-v1.3`. It is not the current API contract.
See [v2 readings](api.md) and the [updated corpus audit](corpus-audit.md).

v1.8 withheld uncertain normalized values and returned document review states. OCR needed
corroboration; unreadable markers, incompatible candidates and low-confidence agreement
could prevent acceptance. Original text and candidates remained available. The policy
reduced accepted errors by reducing coverage; it did not improve the unreadable characters.

Historical cold run, Windows 11 / Python 3.12.13:

| Measurement | Result |
|---|---|
| Inputs | 500 PDFs and one XLSX; no processing failures |
| Former document states | 295 COMPLETE, 206 NEEDS_REVIEW |
| Calls | 44 OCR, no visual provider |
| Duration | 75.568 seconds; 6.63 files/second |
| Provisionally labelled scan fields | 283 |
| Accepted matches | 113 |
| Withheld values | 170 |
| Accepted disagreements | 0 |

These were provisional assistant references. Later human corrections changed the reference
denominator; use the updated audit for comparisons. One concurrent local run is not a
controlled performance benchmark or capacity guarantee.

Historical `scan_025.pdf` invoice number lacked corroboration; `scan_026.pdf` had competing
`F26-7712` and `NF26-7712` readings. Their other nine fields retained matching readings.
Artifacts remain in ignored `backend/reports/abstention-cold/`.

The current API exposes best readings, including single-reader proposals, and produces no
NEEDS_REVIEW/HUMAN_REVIEW decision.
