"""Thread-safe connection reuse; credentials remain scoped to each request."""

import threading
from contextlib import contextmanager

import httpx

from .budget import remaining


class ProviderHTTP:
    def __init__(self):
        self._client = None
        self._lock = threading.Lock()

    @contextmanager
    def session(self, timeout):
        with self._lock:
            if self._client is None:
                self._client = httpx.Client(timeout=timeout, follow_redirects=False)
            client = self._client
        yield _Request(client, timeout)

    def close(self):
        with self._lock:
            if self._client is not None:
                self._client.close()
                self._client = None


class _Request:
    def __init__(self, client, timeout):
        self.client, self.timeout = client, timeout

    def post(self, *args, **kwargs):
        return self.client.post(*args, timeout=remaining(self.timeout), **kwargs)
