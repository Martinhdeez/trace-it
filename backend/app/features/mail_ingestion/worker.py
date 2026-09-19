"""python -m app.features.mail_ingestion.worker [initialize|run|check]."""

import argparse
import asyncio
import contextlib
import imaplib
import logging
import signal
from datetime import UTC, datetime

import httpx

from .config import MailSettings
from .documents import RejectedDocument
from .imap import AuthenticationFailed, Mailbox

log = logging.getLogger(__name__)


class Worker:
    def __init__(self, settings, api, mailbox_factory=Mailbox):
        self.settings, self.api, self.mailbox_factory = settings, api, mailbox_factory
        self.root = f"/mail-ingestion/{settings.process_id}"
        self.stopping = asyncio.Event()
        self.phase = "waiting"

    async def request(self, method, path="", **kwargs):
        response = await self.api.request(method, self.root + path, **kwargs)
        response.raise_for_status()
        return response.json()

    async def state(self):
        state = await self.request("GET")
        if state["state"] == "active" and (
            not state["uidvalidity"]
            or not state["initial_uid"]
            or not state["next_uid"]
            or state["next_uid"] < state["initial_uid"]
        ):
            raise RuntimeError("Persisted mailbox cursor is missing or inconsistent")
        if state["protocol_version"] != 2 or any(
            state[key] != value
            for key, value in (
                ("host", self.settings.imap_host),
                ("username", self.settings.imap_username),
                ("folder", self.settings.imap_folder),
                ("process_id", self.settings.process_id),
            )
        ):
            raise RuntimeError("Worker/backend compatibility or mailbox binding mismatch")
        return state

    async def initialize(self):
        state = await self.state()
        if state["state"] != "uninitialized":
            raise RuntimeError("Cursor already exists; initialization will not reset it")
        # Sample UIDNEXT only once. Messages arriving after EXAMINE belong to the next poll.
        mailbox = self.mailbox_factory(self.settings)
        try:
            await asyncio.to_thread(mailbox.__enter__)
            await self.request(
                "POST",
                "/initialize",
                json={
                    "uidvalidity": mailbox.uidvalidity,
                    "uidnext": mailbox.uidnext,
                },
            )
        finally:
            await asyncio.to_thread(mailbox.__exit__, None, None, None)

    async def process(self, mailbox, message):
        path = f"/messages/{message['id']}"
        headers = {"X-Mail-Lease": message["lease_token"]}
        try:
            if not message["metadata_saved"]:
                manifest = await asyncio.to_thread(mailbox.manifest, message["uid"])
                message = await self.request(
                    "PUT", path + "/manifest", json=manifest, headers=headers
                )
            if message["state"] in ("ignored", "failed"):
                return
            for part in message["attachments"]:
                if part["state"] not in ("discovered", "reading"):
                    continue
                attachment = path + f"/attachments/{part['id']}"
                await self.request("POST", attachment + "/reading", headers=headers)
                try:
                    content = await asyncio.to_thread(mailbox.download, message["uid"], part)
                except RejectedDocument as error:
                    await self.request(
                        "POST",
                        attachment + "/failure",
                        json={"error": str(error), "permanent": True},
                        headers=headers,
                    )
                    continue
                await self.request("PUT", attachment, content=content, headers=headers)
            await self.request("POST", path + "/finish", headers=headers)
        except Exception as error:
            # Only enumerated error codes cross the API/log boundary, never message bodies,
            # credentials, server greetings or provider payloads.
            permanent = isinstance(error, RejectedDocument)
            # Durable lease expiry recovers a lost response/backend outage.
            with contextlib.suppress(httpx.HTTPError):
                await self.request(
                    "POST",
                    path + "/failure",
                    headers=headers,
                    json={
                        "error": str(error) if permanent else "infrastructure_error",
                        "permanent": permanent,
                    },
                )

    async def cycle(self):
        self.phase = "polling"
        state = await self.state()
        if state["state"] != "active":
            raise RuntimeError("Mailbox requires explicit initialization or operator recovery")
        # Imports already committed to PostgreSQL can finish independently of IMAP discovery.
        # Claim filtering guarantees that process() will not need mailbox bytes.
        for _ in range(self.settings.max_messages_per_poll):
            if self.stopping.is_set():
                return
            ready = await self.request("POST", "/claim?ready_only=true")
            if ready is None:
                break
            self.phase = "processing"
            await self.process(None, ready)
        self.phase = "polling"
        if state["retry_at"] and datetime.fromisoformat(state["retry_at"]) > datetime.now(UTC):
            return
        mailbox = self.mailbox_factory(self.settings)
        try:
            await asyncio.to_thread(mailbox.__enter__)
            if mailbox.uidvalidity != state["uidvalidity"]:
                await self.request("POST", "/poll-failure", json={"error": "uidvalidity_changed"})
                raise RuntimeError("UIDVALIDITY changed; account halted")
            through, uids = await asyncio.to_thread(mailbox.discover, state["next_uid"])
            await self.request(
                "POST",
                "/discover",
                json={
                    "uidvalidity": mailbox.uidvalidity,
                    "expected_cursor": state["next_uid"],
                    "through_uid": through,
                    "uids": uids,
                },
            )
            for _ in range(self.settings.max_messages_per_poll):
                if self.stopping.is_set():
                    break
                message = await self.request("POST", "/claim")
                if message is None:
                    break
                self.phase = "processing"
                # Reset bounded message accounting when resuming an already-saved manifest.
                mailbox.connection.remaining_bytes = self.settings.max_message_bytes
                await self.process(mailbox, message)
        except AuthenticationFailed:
            await self.request("POST", "/poll-failure", json={"error": "invalid_credentials"})
            raise RuntimeError("Mailbox authentication refused; account halted") from None
        except (OSError, imaplib.IMAP4.error):
            await self.request("POST", "/poll-failure", json={"error": "imap_unavailable"})
        finally:
            await asyncio.to_thread(mailbox.__exit__, None, None, None)

    async def heartbeat(self):
        while not self.stopping.is_set():
            with contextlib.suppress(httpx.HTTPError):
                await self.request("POST", "/heartbeat", json={"phase": self.phase})
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self.stopping.wait(), timeout=15)

    async def run(self):
        await self.state()  # Reject incompatible releases before announcing a live worker.
        heartbeat = asyncio.create_task(self.heartbeat())
        try:
            await self.run_cycles()
        finally:
            self.stopping.set()
            heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat
            with contextlib.suppress(httpx.HTTPError):
                await self.request("POST", "/heartbeat", json={"phase": "stopped"})

    async def run_cycles(self):
        failures = 0
        while not self.stopping.is_set():
            try:
                await self.cycle()
                failures = 0
            except httpx.HTTPError:
                failures += 1
                log.warning("mail_backend_unavailable")
                if failures >= 6:
                    raise RuntimeError("Backend retry budget exhausted") from None
            delay = min(3600, self.settings.poll_interval_seconds * 2**failures)
            self.phase = "waiting"
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self.stopping.wait(), timeout=delay)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("initialize", "run", "check"), default="run", nargs="?")
    command = parser.parse_args().command
    cfg = MailSettings()
    if command == "check":
        print("mail-ingestion protocol=2; read-only IMAP worker available")
        return
    if command == "run" and not cfg.ingestion_enabled:
        print("Mail ingestion disabled")
        return
    cfg.require_configured()
    async with httpx.AsyncClient(
        base_url=cfg.api_base_url.rstrip("/"),
        headers={"Authorization": "Bearer " + cfg.api_token_file.read_text().strip()},
        timeout=httpx.Timeout(180, connect=cfg.timeout_seconds),
        follow_redirects=False,
    ) as api:
        worker = Worker(cfg, api)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: loop.call_soon_threadsafe(worker.stopping.set))
        if command == "initialize":
            await worker.initialize()
            print("Cursor persisted. No historical messages imported. Worker remains disabled.")
        else:
            await worker.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    try:
        asyncio.run(main())
    except Exception:
        # Never print raw network exceptions, connection strings or credentials.
        log.error("mail_worker_stopped; inspect integration status and configuration")
        raise SystemExit(1) from None
