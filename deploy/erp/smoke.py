"""Read-only probe of the real legacy login, XML and public HTML contracts."""

import json
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


def request(base, path, data=None, token=None):
    headers = {"X-ERP-Token": token} if token else {}
    for attempt in range(8):
        try:
            with urlopen(
                Request(base + path, data=data, headers=headers), timeout=10
            ) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code not in {429, 500} or attempt == 7:
                raise
            time.sleep(1)
    raise AssertionError("Unreachable")


def check(base):
    health = json.loads(request(base, "/healthz"))
    assert health["rows"] == health["expected_rows"]
    login = ET.fromstring(
        request(
            base,
            "/erp/login",
            urlencode({"usuario": "alberto", "clave": "FACTURAS2009"}).encode(),
        )
    )
    token = login.findtext("token")
    assert token
    page = ET.fromstring(request(base, "/erp/asientos?pagina=1", token=token))
    assert int(page.findtext("meta/total")) == health["expected_rows"]
    assert page.findall("asientos/asiento")
    html = request(base, "/nexia/erp/").decode("iso-8859-1")
    assert 'action="/nexia/erp/erp/login"' in html
    print(json.dumps({"release": health["id"], "rows": health["rows"], "smoke": "ok"}))


if __name__ == "__main__":
    check(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8009")
