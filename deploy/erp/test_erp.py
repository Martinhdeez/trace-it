"""Real HTTP tests of the subpath adapter and safe source bootstrap."""

import http.client
import sys
import threading
from pathlib import Path
from urllib.parse import urlencode
from xml.etree import ElementTree

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / ".context/500-sombras-de-alberto"))
sys.path.insert(0, str(HERE))

import server
from bootstrap_sources import bootstrap


@pytest.fixture
def api():
    server.erp.ESTADO = server.erp.EstadoERP(
        server.erp._cargar_asientos_embebidos(), latencia=0
    )
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()

    def request(path, method="GET", fields=None, token=None, reset_rate=True):
        if reset_rate:
            server.erp.ESTADO.ventana.clear()
        conn = http.client.HTTPConnection(*httpd.server_address, timeout=3)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if token:
            headers["X-ERP-Token"] = token
        conn.request(method, path, urlencode(fields) if fields else None, headers)
        result = conn.getresponse()
        response = (
            result.status,
            dict(result.getheaders()),
            result.read().decode("iso-8859-1"),
        )
        conn.close()
        return response

    yield request
    httpd.shutdown()
    httpd.server_close()
    worker.join()


def login(api):
    status, _, body = api(
        "/erp/login", "POST", {"usuario": "alberto", "clave": "FACTURAS2009"}
    )
    assert status == 200
    return ElementTree.fromstring(body).findtext("token")


def test_public_login_links_search_and_pagination_stay_under_subpath(api, capsys):
    status, _, html = api("/nexia/erp/")
    assert status == 200 and 'action="/nexia/erp/erp/login"' in html
    status, headers, _ = api(
        "/nexia/erp/erp/login",
        "POST",
        {
            "usuario": "alberto",
            "clave": "FACTURAS2009",
            "origen": "web",
        },
    )
    assert status == 302
    location = headers["Location"]
    assert location.startswith("/nexia/erp/erp/consulta?token=")
    status, _, html = api(location)
    assert status == 200 and 'action="/nexia/erp/erp/consulta"' in html
    assert 'href="/erp/' not in html and "/nexia/erp/erp/consulta?token=" in html
    assert api(location + "&pagina=2")[0] == 200
    assert api(location + "&asiento=AS-00412")[0] == 200
    assert "token=" not in capsys.readouterr().out


def test_login_failure_and_expired_session_links(api):
    status, headers, _ = api("/nexia/erp/erp/login", "POST", {"origen": "web"})
    assert status == 302 and headers["Location"] == "/nexia/erp/?error=1"
    status, _, body = api("/nexia/erp/erp/consulta?token=expired")
    assert status == 401 and 'href="/nexia/erp/"' in body


def test_original_api_periodic_failure_and_session_expiration(api):
    token = login(api)
    for attempt in range(1, server.erp.FALLO_CADA + 2):
        status, _, body = api("/erp/asientos?pagina=1", token=token)
        assert status == (500 if attempt == server.erp.FALLO_CADA else 200)
        if status == 500:
            assert "ORA-00600" in body
    server.erp.ESTADO.sesiones[token]["usos"] = server.erp.TOKEN_VIGENCIA_USOS
    assert api("/erp/asientos?pagina=1", token=token)[0] == 401


def test_original_rate_limit_and_html_failure(api):
    token = login(api)
    server.erp.ESTADO.consultas_autenticadas = server.erp.FALLO_CADA - 1
    assert api("/nexia/erp/erp/consulta?token=" + token)[0] == 500
    assert api("/nexia/erp/erp/consulta?token=" + token)[0] == 200
    statuses = [
        api("/erp/estado", reset_rate=False)[0]
        for _ in range(server.erp.RATE_MAX_POR_SEGUNDO)
    ]
    assert statuses[-1] == 429


def test_bootstrap_appends_missing_sources_and_preserves_complete_ones():
    loaded, calls = [], []

    def request(path, extra=()):
        calls.append(path)
        if path.endswith("/workbook"):
            loaded.extend(
                {"name": name, "rows": 10}
                for name in ("orders", "suppliers", "parameters")
            )
            assert "cut_off_date=2026-09-18" in extra
            return {"sources": loaded.copy()}
        if path.endswith("/sync"):
            if not any(row["name"] == "erp" for row in loaded):
                loaded.append({"name": "erp", "rows": 500, "status": "ok"})
            return {"rows": 500, "stats": {"retries": 2}}
        return loaded.copy()

    bootstrap(request, 1, "reference.xlsx", "2026-09-18")
    bootstrap(request, 1, "reference.xlsx", "2026-09-18")
    assert calls.count("/processes/1/sources/workbook") == 1
    assert len(loaded) == 4


def test_bootstrap_refuses_partial_existing_references():
    calls = []

    def request(path, extra=()):
        calls.append(path)
        return [{"name": "orders", "rows": 2}]

    with pytest.raises(SystemExit, match="Partial"):
        bootstrap(request, 1, "reference.xlsx", "2026-09-18")
    assert len(calls) == 1
