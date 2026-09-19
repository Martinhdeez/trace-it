import runpy
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPT = Path(__file__).with_name("activate-route.py")


def run_existing(config: bytes, *args: str) -> str | int | None:
    with (
        patch.object(Path, "read_bytes", return_value=config),
        patch.object(sys, "argv", [str(SCRIPT), *args]),
        pytest.raises(SystemExit) as stopped,
    ):
        runpy.run_path(str(SCRIPT), run_name="__main__")
    return stopped.value.code


def test_existing_managed_route_allows_non_semantic_edits() -> None:
    config = b"""gex-dashboard.hopto.org {
    # trace-it managed subpath
    redir   /nexia/trace-it   /nexia/trace-it/   308
    handle /nexia/trace-it/* {
        header X-Deployment production
        reverse_proxy 127.0.0.1:18173
    }
}
"""

    assert run_existing(config) == 0


def test_existing_managed_route_rejects_another_upstream() -> None:
    config = b"""gex-dashboard.hopto.org {
    # trace-it managed subpath
    redir /nexia/trace-it /nexia/trace-it/ 308
    handle /nexia/trace-it/* {
        reverse_proxy 127.0.0.1:9999
    }
}
"""

    assert "route differs" in str(run_existing(config))


def test_existing_criminal_records_route_allows_non_semantic_edits() -> None:
    config = b"""gex-dashboard.hopto.org {
    # trace-it criminal records managed subpath
    redir /nexia/criminal-records /nexia/criminal-records/ 308
    handle /nexia/criminal-records/* {
        header X-Registry synthetic
        reverse_proxy 127.0.0.1:18010
    }
}
"""

    assert run_existing(config, "--criminal-records") == 0
