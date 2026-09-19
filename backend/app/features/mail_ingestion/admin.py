"""Offline operator commands; never connect to IMAP or print a service token."""

import argparse
import asyncio
import hashlib
from pathlib import Path

from sqlalchemy import select

from app.core import events
from app.core.database import session_factory
from app.features.versions.service import active, lock

from .model import MailAccount


async def execute(args):
    async with session_factory() as session:
        process = await lock(session, args.process_id)
        account = await session.scalar(
            select(MailAccount).where(MailAccount.process_id == args.process_id).with_for_update()
        )
        if args.command == "provision":
            if process.gathering_email != args.username:
                raise ValueError("Assign the gathering email in process settings first")
            await active(session, process.id)
            token = args.token_file.read_text().strip()
            if len(token) < 32:
                raise ValueError("Service token must have at least 32 random characters")
            if account:
                raise ValueError(
                    "Mailbox already provisioned; do not replace its identity or cursor"
                )
            account = MailAccount(
                process_id=process.id,
                host=args.host,
                username=args.username,
                folder=args.folder,
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
            )
            session.add(account)
        elif account is None:
            raise ValueError("Mailbox is not provisioned")
        elif args.command == "halt":
            account.state = "halted"
            account.error = "operator_halt"
        elif args.command == "resume":
            if account.state != "halted" or account.error == "uidvalidity_changed":
                raise ValueError(
                    "Cannot resume this state; UIDVALIDITY needs a separate reconciliation"
                )
            if not account.uidvalidity or not account.next_uid:
                raise ValueError("No persisted cursor; restore state before resuming")
            account.state, account.error, account.retry_at = "active", None, None
            account.failures = 0
        events.record(
            session, "mail_operator", process_id=process.id, data={"action": args.command}
        )
        await session.commit()
        print(
            f"Process {process.id}: {process.name}; "
            f"mailbox {account.username}; state {account.state}"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("provision", "halt", "resume"))
    parser.add_argument("--process-id", required=True, type=int)
    parser.add_argument("--host", default="mx1.j-aautomation.com")
    parser.add_argument("--username", default="migration-test@j-aautomation.com")
    parser.add_argument("--folder", default="INBOX")
    parser.add_argument("--token-file", type=Path)
    args = parser.parse_args()
    if args.command == "provision" and args.token_file is None:
        parser.error("provision requires --token-file")
    asyncio.run(execute(args))


if __name__ == "__main__":
    main()
