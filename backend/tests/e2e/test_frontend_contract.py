"""Release gates for the actual live client. Do not xfail integration gaps.

The browser exercises rendering; these checks enumerate route/header/schema drift,
including actions a smoke visit may not click. They intentionally fail on old main.
"""

import re
from pathlib import Path

import pytest

from app.main import app

pytestmark = pytest.mark.e2e
FRONTEND = Path(__file__).resolve().parents[3] / "frontend" / "src" / "api"


def canonical(path: str) -> str:
    path = re.sub(r"\$\{query\(.*?\)\}", "", path)
    return re.sub(r"\$?\{[^}]+\}", "{}", path)


def test_live_client_routes_exist_in_openapi():
    live = (FRONTEND / "live.ts").read_text(encoding="utf-8")
    calls = re.findall(
        r"\b(get|getText|post|put|upload)(?:<[^;\n]*?>)?\(\s*['\"`]([^'\"`]+)['\"`]",
        live,
    )
    assert len(calls) >= 25, "The route audit no longer recognizes the live client"
    methods = {"getText": "get", "upload": "post"}
    routes = {
        (canonical(path), method)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }
    missing = sorted(
        f"{methods.get(method, method).upper()} {path}"
        for method, path in calls
        if (canonical(path), methods.get(method, method)) not in routes
    )
    assert not missing, "Live client calls absent from the API:\n" + "\n".join(missing)


def test_live_client_identity_header_matches_backend():
    http = (FRONTEND / "http.ts").read_text(encoding="utf-8")
    parameters = app.openapi()["paths"]["/me"]["get"]["parameters"]
    header = next(item["name"] for item in parameters if item["in"] == "header")
    assert header.lower() in http.lower(), f"Live client must send {header}"


def test_live_client_user_fields_match_api():
    contract = (FRONTEND / "contracts.ts").read_text(encoding="utf-8")
    user = re.search(r"export type User = \{(.*?)\n\}", contract, re.S)
    assert user
    fields = set(re.findall(r"^\s+(\w+):", user.group(1), re.M))
    schema = app.openapi()["components"]["schemas"]["UserOut"]
    assert fields == set(schema["properties"]), "Map the live API user before rendering it"
