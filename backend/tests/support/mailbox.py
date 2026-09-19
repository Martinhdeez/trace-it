"""Synthetic .eml fixtures served over real loopback IMAP/TLS, with a command ledger."""

import re
import socketserver
import ssl
import threading
from datetime import UTC, datetime, timedelta
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def synthetic_mail(parts=(), subject="Synthetic invoices"):
    msg = EmailMessage()
    msg["From"] = "supplier@example.invalid"
    msg["To"] = "migration-test@j-aautomation.com"
    msg["Subject"] = subject
    msg["Message-ID"] = "<deliberately-repeated@example.invalid>"
    msg["Date"] = "Thu, 01 Jan 1970 00:00:00 +0000"
    msg.set_content("Test data only. No links are followed.")
    for name, content, subtype in parts:
        msg.add_attachment(content, maintype="application", subtype=subtype, filename=name)
    return msg.as_bytes(policy=policy.SMTP)


def quoted(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def structure(message, prefix="", payloads=None):
    if payloads is None:
        payloads = {}
    if message.is_multipart():
        children = [
            structure(part, f"{prefix}.{i}" if prefix else str(i), payloads)[0]
            for i, part in enumerate(message.iter_parts(), 1)
        ]
        return "(" + " ".join(children) + ' "MIXED")', payloads
    part_id = prefix or "1"
    raw = message.get_payload().encode("ascii")
    payloads[part_id] = raw
    major, minor = message.get_content_type().split("/")
    name = message.get_filename()
    disposition = f'("ATTACHMENT" ("FILENAME" {quoted(name)}))' if name else "NIL"
    result = (
        f"({quoted(major.upper())} {quoted(minor.upper())} NIL NIL NIL "
        f"{quoted(message.get('Content-Transfer-Encoding', '7bit').upper())} {len(raw)}"
    )
    if major == "text":
        result += " 1"
    return result + f" NIL {disposition})", payloads


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        fixture = self.server.fixture
        self.wfile.write(b"* OK synthetic IMAP4rev1 ready\r\n")
        while line := self.rfile.readline():
            text = line.decode().rstrip()
            tag, command, *rest = text.split(" ", 2)
            args = rest[0] if rest else ""
            # Store command shape, never credentials, even synthetic ones.
            fixture.commands.append(command + (" " + args if command != "LOGIN" else ""))
            if command == "CAPABILITY":
                self.wfile.write(b"* CAPABILITY IMAP4rev1\r\n")
            elif command == "LOGIN":
                if fixture.refuse_login:
                    self.wfile.write(f"{tag} NO invalid login\r\n".encode())
                    continue
            elif command == "EXAMINE":
                boundary = fixture.next_uid
                self.wfile.write(
                    f"* {len(fixture.messages)} EXISTS\r\n"
                    f"* OK [UIDVALIDITY {fixture.uidvalidity}] valid\r\n"
                    f"* OK [UIDNEXT {boundary}] next\r\n".encode()
                )
                if fixture.on_examine:
                    callback, fixture.on_examine = fixture.on_examine, None
                    callback()
            elif command == "UID" and args.startswith("SEARCH"):
                low, high = map(int, args.rsplit(" ", 1)[-1].split(":"))
                found = " ".join(str(uid) for uid in fixture.messages if low <= uid <= high)
                self.wfile.write(f"* SEARCH {found}\r\n".encode())
            elif command == "UID" and args.startswith("FETCH"):
                uid = int(args.split()[1])
                if uid not in fixture.messages:
                    self.wfile.write(f"{tag} OK absent\r\n".encode())
                    continue
                raw = fixture.messages[uid]
                msg = BytesParser(policy=policy.default).parsebytes(raw)
                tree, payloads = structure(msg)
                if "BODYSTRUCTURE" in args:
                    self.wfile.write(
                        f"* 1 FETCH (UID {uid} RFC822.SIZE {len(raw)} "
                        'INTERNALDATE "19-Sep-2026 12:00:00 +0000" '
                        f"BODYSTRUCTURE {tree})\r\n".encode()
                    )
                else:
                    match = re.search(r"BODY.PEEK\[(.*?)\]<(\d+)\.(\d+)>", args)
                    if not match:
                        fixture.forbidden.append(text)
                        self.wfile.write(f"{tag} BAD unsafe fetch\r\n".encode())
                        continue
                    section, offset, size = match.groups()
                    content = (
                        raw.split(b"\r\n\r\n")[0] + b"\r\n\r\n"
                        if section.startswith("HEADER")
                        else payloads[section]
                    )
                    chunk = content[int(offset) : int(offset) + int(size)]
                    self.wfile.write(
                        f"* 1 FETCH (UID {uid} BODY[{section}]<{offset}> "
                        f"{{{len(chunk)}}}\r\n".encode()
                        + chunk
                        + b")\r\n"
                    )
            elif command == "LOGOUT":
                self.wfile.write(f"* BYE closing\r\n{tag} OK logout\r\n".encode())
                return
            else:
                fixture.forbidden.append(text)
                self.wfile.write(f"{tag} BAD forbidden\r\n".encode())
                continue
            self.wfile.write(f"{tag} OK complete\r\n".encode())


class LocalMailbox:
    def __init__(self, directory):
        self.messages = {}
        self.flags = {}
        self.next_uid = 1
        self.uidvalidity = 817
        self.commands, self.forbidden = [], []
        self.refuse_login = False
        self.on_examine = None
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(UTC) - timedelta(days=1))
            .not_valid_after(datetime.now(UTC) + timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )
        self.cert_path = directory / "test-ca.pem"
        key_path = directory / "test-key.pem"
        self.cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.cert_path, key_path)
        self.server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.server.fixture = self
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def deliver(self, raw, seen=False):
        uid = self.next_uid
        self.next_uid += 1
        self.messages[uid] = raw
        self.flags[uid] = ("\\Seen",) if seen else ()
        return uid

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
