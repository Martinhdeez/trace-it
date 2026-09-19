"""Host the unmodified challenge ERP, including its faults, under a public subpath."""

import hashlib
import json
import re
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import alberto_erp as erp

PREFIX = "/nexia/erp"
RELEASE = None


class Handler(erp.ManejadorERP):
    def _dispatch(self, method):
        # Internal callers keep the original /erp/* API. Only public requests
        # receive prefixed HTML links and redirects; never trust forwarded headers.
        self.public_prefix = PREFIX if self.path.startswith(PREFIX + "/") else ""
        if self.public_prefix:
            self.path = self.path[len(PREFIX) :]
        getattr(super(), method)()

    def do_GET(self):
        if urlsplit(self.path).path in {"/healthz", PREFIX + "/healthz"} and RELEASE:
            body = json.dumps({**RELEASE, "rows": len(erp.ESTADO.asientos)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._dispatch("do_GET")

    def do_POST(self):
        self._dispatch("do_POST")

    def _responder(self, codigo, cuerpo, tipo="text/xml", extra=None):
        if tipo == "text/html" and self.public_prefix:
            cuerpo = re.sub(r'((?:href|action)=["\'])/(?!/)', rf"\1{PREFIX}/", cuerpo)
        super()._responder(codigo, cuerpo, tipo, extra)

    def _redirigir(self, destino):
        super()._redirigir(self.public_prefix + destino)

    def log_message(self, formato, *args):
        # The original frontend carries session tokens in URLs. Do not log them.
        print(f"ERP {self.command} {urlsplit(self.path).path}", flush=True)


def initialize(directory=None):
    global RELEASE
    directory = directory or Path(__file__).resolve().parent
    erp.ESTADO = erp.EstadoERP(erp._cargar_asientos_embebidos(), latencia=0.12)
    manifest_path = directory / "release.json"
    RELEASE = None
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for name, digest in manifest["sha256"].items():
            if hashlib.sha256((directory / name).read_bytes()).hexdigest() != digest:
                raise ValueError(f"Release checksum mismatch: {name}")
        for name in manifest["updates"]:
            erp.ESTADO.cargar_lote2(erp._cargar_asientos_csv(str(directory / name)))
        if len(erp.ESTADO.asientos) != manifest["expected_rows"]:
            raise ValueError("ERP row count does not match release manifest")
        RELEASE = manifest


def main():
    initialize()
    server = ThreadingHTTPServer(("0.0.0.0", 8009), Handler)
    server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    main()
