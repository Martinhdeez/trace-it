"""Host the unmodified challenge ERP, including its faults, under a public subpath."""

import re
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

import alberto_erp as erp

PREFIX = "/nexia/erp"


class Handler(erp.ManejadorERP):
    def _dispatch(self, method):
        # Internal callers keep the original /erp/* API. Only public requests
        # receive prefixed HTML links and redirects; never trust forwarded headers.
        self.public_prefix = PREFIX if self.path.startswith(PREFIX + "/") else ""
        if self.public_prefix:
            self.path = self.path[len(PREFIX) :]
        getattr(super(), method)()

    def do_GET(self):
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


def main():
    erp.ESTADO = erp.EstadoERP(erp._cargar_asientos_embebidos(), latencia=0.12)
    server = ThreadingHTTPServer(("0.0.0.0", 8009), Handler)
    server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    main()
