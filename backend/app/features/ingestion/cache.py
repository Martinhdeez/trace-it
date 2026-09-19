"""Content identities and reusable reader output, independent of field interpretation."""

import hashlib
import json
import os
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from filelock import FileLock

_usage = ContextVar("extraction_reader_usage", default=None)
_usage_lock = threading.Lock()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


@lru_cache(maxsize=256)
def _file_digest(path, size, modified, changed):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def file_identity(path):
    """Hash bytes once per file revision; paths and timestamps are not identities."""
    path = Path(path)
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return _file_digest(str(path.resolve()), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def source_identity(*paths):
    return {Path(path).name: file_identity(path) for path in paths}


@lru_cache(maxsize=32)
def package_version(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def count_reader(name):
    usage = _usage.get()
    if usage is not None:
        with _usage_lock:
            usage[name] = usage.get(name, 0) + 1


@contextmanager
def reader_usage():
    usage = {}
    token = _usage.set(usage)
    try:
        yield usage
    finally:
        _usage.reset(token)


def cached_read(directory, identity, read, validate=lambda value: value, force=False):
    """Serialize identical local work across processes; never cache failed reads."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (fingerprint(identity) + ".json")
    with FileLock(str(path) + ".lock", timeout=300):
        if path.exists() and not force:
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                if (
                    isinstance(record, dict)
                    and record.get("identity") == identity
                    and isinstance(record.get("lines"), list)
                ):
                    result = validate(record["lines"])
                    count_reader("ocr_cache_hits")
                    return result
            except (ValueError, OSError):
                pass  # A corrupt local cache can safely be recomputed.
        result = read()
        temporary = path.with_suffix(".part")
        try:
            temporary.write_text(
                json.dumps({"identity": identity, "lines": result}, ensure_ascii=False),
                encoding="utf-8",
            )
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return result
