import imaplib
import ssl

import pytest

from app.features.ingestion.tests.conftest import pdf_bytes
from app.features.mail_ingestion.config import MailSettings
from app.features.mail_ingestion.documents import RejectedDocument, safe_name, validate_pdf
from app.features.mail_ingestion.imap import Mailbox, ReadOnlyIMAP, candidates, parse_structure
from tests.support.mailbox import LocalMailbox, synthetic_mail


@pytest.fixture
def local_mail(tmp_path, monkeypatch):
    server = LocalMailbox(tmp_path)
    context = ssl.create_default_context(cafile=str(server.cert_path))
    monkeypatch.setattr(ssl, "create_default_context", lambda: context)
    password = tmp_path / "password"
    password.write_text("synthetic-mail-only")
    cfg = MailSettings(
        imap_host="localhost",
        imap_port=server.port,
        imap_username="migration-test@j-aautomation.com",
        imap_password_file=password,
        process_id=37,
    )
    try:
        yield server, cfg
    finally:
        server.close()


def test_real_protocol_uses_examine_peek_and_never_unseen(local_mail):
    server, cfg = local_mail
    pdf = pdf_bytes("Synthetic invoice")
    uid = server.deliver(synthetic_mail([("../../invoice.pdf", pdf, "octet-stream")]), seen=True)
    before = dict(server.messages), dict(server.flags)
    with Mailbox(cfg) as mailbox:
        assert mailbox.uidvalidity == server.uidvalidity
        assert mailbox.discover(uid) == (uid, [uid])
        manifest = mailbox.manifest(uid)
        assert manifest["parts"][0]["part"] == "2"
        assert mailbox.download(uid, manifest["parts"][0]) == pdf
        assert mailbox.discover(uid + 1) == (uid, [])
    assert before == (server.messages, server.flags)
    assert not server.forbidden
    assert any(command.startswith("EXAMINE") for command in server.commands)
    assert not any("UNSEEN" in command for command in server.commands)
    assert all("BODY.PEEK" in c or "BODYSTRUCTURE" in c for c in server.commands if "FETCH" in c)


@pytest.mark.parametrize(
    "command,args",
    [
        ("STORE", ()),
        ("MOVE", ()),
        ("COPY", ()),
        ("APPEND", ()),
        ("EXPUNGE", ()),
        ("CLOSE", ()),
        ("SELECT", ()),
        ("CREATE", ()),
        ("UID", ("STORE", "1", "+FLAGS")),
        ("UID", ("FETCH", "1", "(BODY[1])")),
    ],
)
def test_command_guard_rejects_mailbox_writes(command, args):
    connection = object.__new__(ReadOnlyIMAP)
    with pytest.raises(RuntimeError):
        connection._command(command, *args)


def test_literal_limit_checked_before_reading_or_allocating():
    connection = object.__new__(ReadOnlyIMAP)
    connection.literal_limit, connection.remaining_bytes = 10, 100
    connection.shutdown = lambda: None
    with pytest.raises(RejectedDocument, match="size_limit"):
        connection.read(11)


def test_size_limits_before_fetching_parts(local_mail):
    server, cfg = local_mail
    uid = server.deliver(synthetic_mail([("invoice.pdf", pdf_bytes("x"), "pdf")]))
    cfg.max_message_bytes = 20
    with Mailbox(cfg) as mailbox, pytest.raises(RejectedDocument, match="size_limit"):
        mailbox.manifest(uid)
    assert not any("BODY.PEEK" in c for c in server.commands)


def test_corrupt_encrypted_and_fake_pdf():
    import pymupdf

    for content in (b"fake", b"%PDF-1.7 broken %%EOF", pdf_bytes("x")[:-30]):
        with pytest.raises(RejectedDocument):
            validate_pdf(content, 20971520)
    with pymupdf.open(stream=pdf_bytes("x"), filetype="pdf") as doc:
        encrypted = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="o", user_pw="u")
    with pytest.raises(RejectedDocument):
        validate_pdf(encrypted, 20971520)
    with pytest.raises(RejectedDocument, match="size_limit"):
        validate_pdf(pdf_bytes("x"), 5)


def test_nested_message_and_zip_not_processed():
    tree = parse_structure(
        b'BODYSTRUCTURE (("MESSAGE" "RFC822" NIL NIL NIL "7BIT" 300 NIL NIL NIL)'
        b' ("APPLICATION" "ZIP" NIL NIL NIL "BASE64" 10 NIL NIL) "MIXED")'
    )
    assert candidates(tree) == []
    assert "/" not in safe_name("../../a.pdf", "37-2")
    assert "\\" not in safe_name("C:\\a.pdf", "37-2")


def test_disabled_default_and_incomplete_configuration():
    cfg = MailSettings()
    assert not cfg.ingestion_enabled and cfg.worker_concurrency == 1
    with pytest.raises(ValueError):
        cfg.require_configured()


def test_pdf_limit_applies_during_partial_download_even_when_size_lies(local_mail):
    server, cfg = local_mail
    uid = server.deliver(synthetic_mail([("large.pdf", b"x" * 300000, "pdf")]))
    cfg.max_pdf_bytes = 50000
    with Mailbox(cfg) as mailbox:
        part = mailbox.manifest(uid)["parts"][0]
        part["advertised_size"] = 0
        with pytest.raises(RejectedDocument, match="size_limit"):
            mailbox.download(uid, part)
    downloads = [c for c in server.commands if "BODY.PEEK[2]" in c]
    assert len(downloads) == 2


def test_candidate_count_limit_precedes_part_download(local_mail):
    server, cfg = local_mail
    cfg.max_pdfs_per_message = 1
    uid = server.deliver(
        synthetic_mail(
            [
                ("a.pdf", pdf_bytes("a"), "pdf"),
                ("b.pdf", pdf_bytes("b"), "pdf"),
            ]
        )
    )
    with Mailbox(cfg) as mailbox, pytest.raises(RejectedDocument, match="size_limit"):
        mailbox.manifest(uid)
    assert not any("BODY.PEEK" in c for c in server.commands)


def test_tls_hostname_is_checked(local_mail):
    _, cfg = local_mail
    cfg.imap_host = "127.0.0.1"  # Certificate contains only localhost.
    with pytest.raises(ssl.SSLCertVerificationError), Mailbox(cfg):
        pytest.fail("Hostname verification was bypassed")


def test_discovery_uses_bounded_numeric_ranges(local_mail):
    server, cfg = local_mail
    for _ in range(30):
        server.deliver(synthetic_mail(), seen=True)
    with Mailbox(cfg) as mailbox:
        through, uids = mailbox.discover(5)
    assert through == 24 and uids == list(range(5, 25))
    assert "UID SEARCH UID 5:24" in server.commands


def test_international_filename_parameters_are_preserved():
    tree = [
        "APPLICATION",
        "OCTET-STREAM",
        None,
        None,
        None,
        "BASE64",
        12,
        None,
        ["ATTACHMENT", ["filename*", "utf-8''factura%20caf%C3%A9.pdf"]],
    ]
    assert candidates(tree)[0]["original_name"] == "factura café.pdf"


def test_disconnect_during_login_is_not_a_credential_rejection(local_mail, monkeypatch):
    _, cfg = local_mail

    def disconnected(*args):
        raise imaplib.IMAP4.abort("Synthetic dropped connection")

    monkeypatch.setattr(ReadOnlyIMAP, "login", disconnected)
    mailbox = Mailbox(cfg)
    try:
        with pytest.raises(imaplib.IMAP4.abort):
            mailbox.__enter__()
    finally:
        mailbox.__exit__()
