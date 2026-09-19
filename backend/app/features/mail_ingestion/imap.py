"""Bounded IMAP over verified TLS. No SMTP and no mailbox write commands."""

import base64
import binascii
import contextlib
import imaplib
import quopri
import re
import ssl
from email import policy
from email.header import decode_header, make_header
from email.parser import BytesHeaderParser

from .documents import RejectedDocument, validate_pdf


class AuthenticationFailed(Exception):
    pass


class ReadOnlyIMAP(imaplib.IMAP4_SSL):
    literal_limit = 65536
    remaining_bytes = 52428800

    def _command(self, name, *args):
        if name not in ("CAPABILITY", "LOGIN", "EXAMINE", "UID", "LOGOUT"):
            raise RuntimeError("Mailbox write or unsupported command refused")
        if name == "UID":
            operation = str(args[0]).upper()
            if operation not in ("SEARCH", "FETCH"):
                raise RuntimeError("Mailbox write refused")
            if operation == "FETCH":
                query = str(args[-1]).upper()
                if "BODY[" in query or "RFC822)" in query or "RFC822.TEXT" in query:
                    raise RuntimeError("Non-PEEK fetch refused")
        return super()._command(name, *args)

    def read(self, size):
        # imaplib otherwise buffers any server-announced literal in full.
        if size > self.literal_limit or size > self.remaining_bytes:
            self.shutdown()
            raise RejectedDocument("size_limit")
        self.remaining_bytes -= size
        return super().read(size)


def parse_structure(data: bytes):
    """Parse the bounded parenthesized BODYSTRUCTURE grammar, never eval server text."""
    tokens = re.findall(rb'"(?:[^"\\]|\\.)*"|[()]|[^\s()]+', data)
    position = 0

    def value(depth=0):
        nonlocal position
        if depth > 32 or position >= len(tokens):
            raise RejectedDocument("invalid_mime")
        token = tokens[position]
        position += 1
        if token == b"(":
            result = []
            while position < len(tokens) and tokens[position] != b")":
                result.append(value(depth + 1))
            if position >= len(tokens):
                raise RejectedDocument("invalid_mime")
            position += 1
            return result
        if token.startswith(b'"'):
            return re.sub(rb"\\(.)", rb"\1", token[1:-1]).decode("utf-8", "replace")
        if token.upper() == b"NIL":
            return None
        return int(token) if token.isdigit() else token.decode("ascii", "replace")

    offset = data.upper().find(b"BODYSTRUCTURE ")
    if offset < 0:
        raise RejectedDocument("invalid_mime")
    tokens = re.findall(rb'"(?:[^"\\]|\\.)*"|[()]|[^\s()]+', data[offset + 14 :])
    try:
        return value()
    except (IndexError, TypeError, ValueError) as exc:
        raise RejectedDocument("invalid_mime") from exc


def candidates(tree, prefix=""):
    if not isinstance(tree, list) or not tree:
        raise RejectedDocument("invalid_mime")
    if isinstance(tree[0], list):
        result = []
        for number, child in enumerate(tree, 1):
            if not isinstance(child, list):
                break
            result.extend(candidates(child, f"{prefix}.{number}" if prefix else str(number)))
        return result
    if len(tree) < 7:
        raise RejectedDocument("invalid_mime")
    kind = f"{tree[0]}/{tree[1]}".lower()
    # In particular, message/rfc822 never recurses.
    if kind not in ("application/pdf", "application/octet-stream"):
        return []
    params = tree[2] or []
    attributes = {str(params[i]).lower(): params[i + 1] for i in range(0, len(params) - 1, 2)}
    disposition = tree[8] if len(tree) > 8 else None
    if isinstance(disposition, list) and len(disposition) > 1:
        params = disposition[1] or []
        attributes.update(
            {str(params[i]).lower(): params[i + 1] for i in range(0, len(params) - 1, 2)}
        )
    name = str(attributes.get("filename") or attributes.get("name") or "attachment.pdf")
    with contextlib.suppress(ValueError, LookupError):
        name = str(make_header(decode_header(name)))
    if kind == "application/octet-stream" and not name.lower().endswith(".pdf"):
        return []
    if not isinstance(tree[6], int) or tree[6] < 0:
        raise RejectedDocument("invalid_mime")
    return [
        {
            "part": prefix or "1",
            "original_name": name[:512],
            "encoding": str(tree[5]).lower(),
            "advertised_size": tree[6],
        }
    ]


class Mailbox:
    def __init__(self, settings):
        self.settings = settings
        self.connection = None

    def __enter__(self):
        cfg = self.settings
        self.connection = ReadOnlyIMAP(
            cfg.imap_host,
            cfg.imap_port,
            ssl_context=ssl.create_default_context(),
            timeout=cfg.timeout_seconds,
        )
        self.connection.sock.settimeout(cfg.timeout_seconds)
        try:
            self.connection.login(cfg.imap_username, cfg.imap_password_file.read_text().strip())
        except imaplib.IMAP4.error as exc:
            self.connection.shutdown()
            raise AuthenticationFailed("Mailbox authentication failed") from exc
        self._ok(
            self.connection.select(
                '"' + cfg.imap_folder.replace("\\", "\\\\").replace('"', '\\"') + '"',
                readonly=True,
            )
        )
        self.uidvalidity = int(self.connection.response("UIDVALIDITY")[1][0])
        self.uidnext = int(self.connection.response("UIDNEXT")[1][0])
        return self

    def __exit__(self, *args):
        if self.connection:
            with contextlib.suppress(OSError, imaplib.IMAP4.error):
                self.connection.logout()

    @staticmethod
    def _ok(response):
        status, data = response
        if status != "OK":
            raise OSError("IMAP request failed")
        return data

    def discover(self, cursor):
        through = min(self.uidnext - 1, cursor + self.settings.max_messages_per_poll - 1)
        if through < cursor:
            return cursor - 1, []
        data = self._ok(self.connection.uid("SEARCH", None, "UID", f"{cursor}:{through}"))
        # Explicit bounds also defeat reversed/empty IMAP range semantics.
        uids = sorted({int(uid) for uid in data[0].split() if cursor <= int(uid) <= through})
        return through, uids

    def _fetch(self, uid, query):
        data = self._ok(self.connection.uid("FETCH", str(uid), query))
        if not data or data == [None]:
            raise RejectedDocument("message_missing")
        return data

    def manifest(self, uid):
        self.connection.remaining_bytes = self.settings.max_message_bytes
        self.connection.literal_limit = 65536
        rows = self._fetch(uid, "(UID RFC822.SIZE INTERNALDATE BODYSTRUCTURE)")
        metadata = b" ".join(
            row
            if isinstance(row, bytes)
            else (
                re.sub(rb"\{[0-9]+\}$", b"", row[0])
                + b'"'
                + row[1].replace(b"\\", b"\\\\").replace(b'"', b'\\"')
                + b'"'
            )
            for row in rows
            if row
        )
        if len(metadata) > 65536:
            raise RejectedDocument("size_limit")
        size_match = re.search(rb"RFC822.SIZE (\d+)", metadata, re.I)
        if not size_match:
            raise RejectedDocument("invalid_mime")
        size = int(size_match[1])
        if size > self.settings.max_message_bytes:
            raise RejectedDocument("size_limit")
        parts = candidates(parse_structure(metadata))
        if len(parts) > self.settings.max_pdfs_per_message:
            raise RejectedDocument("size_limit")
        date = re.search(rb'INTERNALDATE "([^"]*)"', metadata, re.I)
        headers = self._fetch(
            uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT MESSAGE-ID DATE)]<0.8192>)"
        )
        raw = b"".join(row[1] for row in headers if isinstance(row, tuple))
        if len(raw) > 8192:
            raise RejectedDocument("size_limit")
        msg = BytesHeaderParser(policy=policy.default).parsebytes(raw)
        return {
            "size": size,
            "parts": parts,
            "sender": str(msg.get("From", ""))[:1000],
            "subject": str(msg.get("Subject", ""))[:1000],
            "message_id": str(msg.get("Message-ID", ""))[:1000],
            "sent_at": str(msg.get("Date", ""))[:100],
            "internal_date": date[1].decode("ascii", "replace") if date else "",
        }

    def download(self, uid, part):
        cfg = self.settings
        encoding, advertised = part["encoding"], part["advertised_size"]
        # Encoded data has its own bound, as does decoded PDF data.
        encoded_limit = min(cfg.max_message_bytes, cfg.max_pdf_bytes * 2)
        if advertised > encoded_limit:
            raise RejectedDocument("size_limit")
        if encoding not in ("base64", "quoted-printable", "7bit", "8bit", "binary"):
            raise RejectedDocument("invalid_mime")
        if not re.fullmatch(r"[1-9][0-9]*(\.[1-9][0-9]*)*", part["part"]):
            raise RejectedDocument("invalid_mime")
        content = bytearray()
        carry = b""
        offset = 0
        padded = False
        while True:
            count = min(65536, encoded_limit + 1 - offset)
            self.connection.literal_limit = count
            rows = self._fetch(uid, f"(BODY.PEEK[{part['part']}]<{offset}.{count}>)")
            chunks = [row[1] for row in rows if isinstance(row, tuple)]
            if len(chunks) != 1:
                raise RejectedDocument("invalid_mime")
            chunk = chunks[0]
            if len(chunk) > count or offset + len(chunk) > encoded_limit:
                raise RejectedDocument("size_limit")
            offset += len(chunk)
            final = len(chunk) < count
            try:
                if encoding == "base64":
                    block = carry + re.sub(rb"\s", b"", chunk)
                    if padded and block:
                        raise RejectedDocument("invalid_pdf")
                    cut = len(block) if final else len(block) // 4 * 4
                    carry = block[cut:]
                    decoded = base64.b64decode(block[:cut], validate=True)
                    padded = padded or b"=" in block[:cut]
                elif encoding == "quoted-printable":
                    block = carry + chunk
                    cut = len(block)
                    if not final and (last := block.rfind(b"=")) >= max(0, len(block) - 2):
                        cut = last
                    carry, decoded = block[cut:], quopri.decodestring(block[:cut])
                else:
                    decoded = chunk
                if len(content) + len(decoded) > cfg.max_pdf_bytes:
                    raise RejectedDocument("size_limit")
                content.extend(decoded)
            except (ValueError, binascii.Error) as exc:
                if isinstance(exc, RejectedDocument):
                    raise
                raise RejectedDocument("invalid_pdf") from exc
            if final:
                break
        validate_pdf(content, cfg.max_pdf_bytes)
        return bytes(content)
