"""Add only trace-it's subpath after the stack is healthy; validate before reload."""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def managed_route_matches(
    contents: bytes, marker: bytes, route: bytes, upstream: bytes
) -> bool:
    if marker not in contents:
        return False
    redirect = re.search(
        rb"(?m)^[ \t]*redir[ \t]+"
        + re.escape(route)
        + rb"[ \t]+"
        + re.escape(route + b"/")
        + rb"[ \t]+308[ \t]*(?:\r?\n|$)",
        contents,
    )
    handler = re.search(
        rb"handle[ \t]+" + re.escape(route) + rb"/\*[ \t]*\{(?P<body>[^{}]*)\}",
        contents,
        re.DOTALL,
    )
    if redirect is None or handler is None:
        return False
    return bool(
        re.search(
            rb"(?m)^[ \t]*reverse_proxy[ \t]+"
            + re.escape(upstream)
            + rb"(?:[ \t\r\n]|$)",
            handler.group("body"),
        )
    )


config = Path("/etc/caddy/Caddyfile")
original = config.read_bytes()
marker = b"# trace-it managed subpath"
snippet = b"""\t# trace-it managed subpath
\tredir /nexia/trace-it /nexia/trace-it/ 308
\thandle /nexia/trace-it/* {
\t\treverse_proxy 127.0.0.1:18173
\t}

"""
route = b"/nexia/trace-it"
upstream = b"127.0.0.1:18173"
if sys.argv[1:] == ["--erp"]:
    marker = b"# trace-it ERP managed subpath"
    snippet = snippet.replace(b"# trace-it managed subpath", marker)
    snippet = snippet.replace(b"/nexia/trace-it", b"/nexia/erp")
    snippet = snippet.replace(b"127.0.0.1:18173", b"127.0.0.1:18009")
    route = b"/nexia/erp"
    upstream = b"127.0.0.1:18009"
elif sys.argv[1:] == ["--criminal-records"]:
    marker = b"# trace-it criminal records managed subpath"
    snippet = snippet.replace(b"# trace-it managed subpath", marker)
    snippet = snippet.replace(b"/nexia/trace-it", b"/nexia/criminal-records")
    snippet = snippet.replace(b"127.0.0.1:18173", b"127.0.0.1:18010")
    route = b"/nexia/criminal-records"
    upstream = b"127.0.0.1:18010"
elif sys.argv[1:]:
    raise SystemExit("Usage: activate-route.py [--erp|--criminal-records]")
if marker in original:
    if not managed_route_matches(original, marker, route, upstream):
        raise SystemExit(
            f"Existing {route.decode()} route differs; inspect it instead of overwriting it"
        )
    raise SystemExit(0)
if route in original:
    raise SystemExit("An existing trace-it route needs operator review")
anchor = b"\thandle_path /nexia/* {"
if original.count(anchor) != 1 or original.count(b"gex-dashboard.hopto.org {") != 1:
    raise SystemExit(
        "Caddy layout changed; place deploy/caddy-route.conf in the domain manually"
    )
candidate = original.replace(anchor, snippet + anchor, 1)
descriptor, filename = tempfile.mkstemp(
    prefix="trace-it-", suffix=".caddy", dir=config.parent
)
staged = Path(filename)
try:
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(candidate)
    staged.chmod(0o644)
    subprocess.run(
        ["caddy", "validate", "--config", str(staged), "--adapter", "caddyfile"],
        check=True,
    )
    if config.read_bytes() != original:
        raise SystemExit(
            "Caddy was changed concurrently; retry after reviewing the new configuration"
        )
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup = config.with_name(f"Caddyfile.before-trace-it-{stamp}")
    shutil.copy2(config, backup)
    os.replace(staged, config)
    try:
        subprocess.run(["systemctl", "reload", "caddy"], check=True)
    except subprocess.CalledProcessError:
        if (
            hashlib.sha256(config.read_bytes()).digest()
            == hashlib.sha256(candidate).digest()
        ):
            shutil.copy2(backup, config)
            subprocess.run(["systemctl", "reload", "caddy"], check=True)
        raise
finally:
    staged.unlink(missing_ok=True)
