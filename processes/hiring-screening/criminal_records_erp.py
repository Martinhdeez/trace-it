#!/usr/bin/env python3
"""Synthetic legacy criminal-records service for the hiring discovery demo.

It deliberately resembles the challenge ERP: ISO-8859-1 XML and page-number pagination.
Unlike the challenge fixture, this service is reliable and needs no authentication.
It uses only the Python standard library and is evidence for process discovery. It is
not a process definition and does not decide whether somebody should be hired.
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from xml.sax.saxutils import escape

PAGE_SIZE = 10
VERSION = "Registro Central · bridge legacy 1.4 (2009)"
PUBLIC_PREFIX = "/nexia/criminal-records"

# Synthetic records. Ana Molina also appears in the committed hiring CV corpus. The
# remaining people do not. Name-only identity is intentionally visible as a limitation
# for the manager to resolve when the process integration is proposed.
RECORDS = [
    {
        "record_id": f"CR-{number:05d}",
        "full_name": name,
        "conviction_date": date,
        "offense": offense,
        "status": status,
    }
    for number, (name, date, offense, status) in enumerate(
        [
            ("Ana Molina", "2024-05-12", "Fraud", "ACTIVE"),
            ("Alberto Robles", "2021-02-18", "Identity theft", "ACTIVE"),
            ("Beatriz Soler", "2018-07-03", "Forgery", "SPENT"),
            ("Carlos Méndez", "2020-11-21", "Fraud", "ACTIVE"),
            ("Daniela Ferrer", "2017-01-14", "Theft", "SPENT"),
            ("Eduardo Núñez", "2023-09-09", "Bribery", "ACTIVE"),
            ("Fátima Rojas", "2019-06-30", "Forgery", "ACTIVE"),
            ("Guillermo Santos", "2016-03-17", "Theft", "SPENT"),
            ("Helena Ibáñez", "2022-12-02", "Fraud", "ACTIVE"),
            ("Iker Montes", "2020-04-25", "Identity theft", "ACTIVE"),
            ("Jimena Pascual", "2015-08-19", "Forgery", "SPENT"),
            ("Kevin Lozano", "2024-01-07", "Fraud", "ACTIVE"),
            ("Laura Espejo", "2019-10-28", "Theft", "ACTIVE"),
            ("Manuel Varela", "2018-05-16", "Bribery", "SPENT"),
            ("Nerea Salas", "2021-07-11", "Forgery", "ACTIVE"),
            ("Oriol Pastor", "2017-09-23", "Fraud", "SPENT"),
            ("Paula Crespo", "2023-02-04", "Identity theft", "ACTIVE"),
            ("Raúl Esteban", "2020-06-15", "Theft", "ACTIVE"),
            ("Silvia Marín", "2016-12-08", "Forgery", "SPENT"),
            ("Teo Gallardo", "2022-03-29", "Fraud", "ACTIVE"),
            ("Úrsula Bravo", "2019-01-20", "Bribery", "ACTIVE"),
            ("Víctor Segura", "2018-10-06", "Theft", "SPENT"),
            ("Yolanda Rey", "2024-06-13", "Forgery", "ACTIVE"),
        ],
        start=1,
    )
]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "CentralRecordsBridge/1.4"
    sys_version = ""

    def log_message(self, format: str, *args: object) -> None:
        print(f"[criminal-records] {format % args}")

    def respond(self, status: int, body: str, headers: dict[str, str] | None = None) -> None:
        payload = body.encode("iso-8859-1", errors="replace")
        self.send_response(status)
        self.send_header("Content-Type", "text/xml; charset=ISO-8859-1")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-System-Version", "1.4-2009")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == PUBLIC_PREFIX or path == PUBLIC_PREFIX + "/":
            path = "/criminal/status"
        elif path.startswith(PUBLIC_PREFIX + "/"):
            path = path[len(PUBLIC_PREFIX) :]
        if path == "/criminal/status":
            self.respond(
                200,
                f"<status><records>{len(RECORDS)}</records><system>ONLINE</system></status>",
            )
            return
        if path != "/criminal/records":
            self.respond(404, "<error><code>REG-404</code></error>")
            return
        try:
            page = int(parse_qs(parsed.query).get("page", ["1"])[0])
        except ValueError:
            self.respond(400, "<error><code>REG-400</code></error>")
            return
        pages = (len(RECORDS) + PAGE_SIZE - 1) // PAGE_SIZE
        if page < 1 or page > pages:
            self.respond(404, "<error><code>REG-404</code></error>")
            return
        selected = RECORDS[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]
        records = "".join(
            "<record>"
            f"<id>{escape(row['record_id'])}</id>"
            f"<name>{escape(row['full_name'])}</name>"
            f"<conviction_date>{escape(row['conviction_date'])}</conviction_date>"
            f"<offense>{escape(row['offense'])}</offense>"
            f"<status>{escape(row['status'])}</status>"
            "</record>"
            for row in selected
        )
        self.respond(
            200,
            "<response><meta>"
            f"<total>{len(RECORDS)}</total><pages>{pages}</pages>"
            f"</meta><records>{records}</records></response>",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=VERSION)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[criminal-records] {VERSION}")
    print(
        f"[criminal-records] listening on http://{args.host}:{args.port}, records: {len(RECORDS)}"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
