import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from app.features.sources.http_connector import HttpSourceConfig, SourcesFile

REPO = Path(__file__).resolve().parents[5]
ERP_SCRIPT = REPO / ".context/500-sombras-de-alberto/alberto_erp.py"
SOURCES_JSON = REPO / "processes/invoice-payment/sources.json"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_erp(*args: str) -> tuple[subprocess.Popen, str]:
    """The challenge ERP as a subprocess, without its artificial latency."""
    if not ERP_SCRIPT.is_file():
        pytest.skip("challenge submodule not checked out (git submodule update --init)")
    port = _free_port()
    process = subprocess.Popen(
        [sys.executable, str(ERP_SCRIPT), "--puerto", str(port), "--rapido", *args],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            httpx.get(f"{url}/erp/estado", timeout=0.5)
            return process, url
        except httpx.TransportError:
            time.sleep(0.05)
    process.kill()
    raise RuntimeError("the ERP did not start")


@pytest.fixture
def erp() -> Iterator[str]:
    process, url = start_erp()
    yield url
    process.kill()
    process.wait()


@pytest.fixture(autouse=True)
def erp_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    # The demo credentials documented in .env.example; tests never read a real .env.
    monkeypatch.setenv("TRACE_ERP_USER", "alberto")
    monkeypatch.setenv("TRACE_ERP_PASSWORD", "FACTURAS2009")


def erp_config(url: str, **overrides: dict) -> HttpSourceConfig:
    """The pack's real ERP configuration, pointed at `url`, with sections overridden."""
    data = SourcesFile.model_validate_json(SOURCES_JSON.read_text()).sources["erp"].model_dump()
    data["base_url"] = {"env": "TRACE_TEST_UNSET_VARIABLE", "default": url}
    for section, values in overrides.items():
        data[section] = {**(data[section] or {}), **values}
    return HttpSourceConfig.model_validate(data)
