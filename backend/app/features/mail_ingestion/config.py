from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MailSettings(BaseSettings):
    # Deliberately do not load the backend's .env or any provider credentials.
    model_config = SettingsConfigDict(env_prefix="MAIL_", extra="ignore")

    ingestion_enabled: bool = False
    imap_host: str = ""
    imap_port: int = Field(default=993, ge=1, le=65535)
    imap_username: str = ""
    imap_password_file: Path | None = None
    imap_folder: str = "INBOX"
    poll_interval_seconds: int = Field(default=60, ge=1)
    process_id: int = Field(default=0, ge=0)
    api_base_url: str = ""
    api_token_file: Path | None = None
    max_pdf_bytes: int = Field(default=20971520, ge=1, le=20971520)
    max_message_bytes: int = Field(default=52428800, ge=1, le=52428800)
    max_pdfs_per_message: int = Field(default=10, ge=1, le=100)
    max_messages_per_poll: int = Field(default=20, ge=1, le=100)
    worker_concurrency: int = Field(default=1, ge=1, le=1)
    timeout_seconds: int = Field(default=30, ge=1, le=120)

    @model_validator(mode="after")
    def safe_strings(self):
        for value in (self.imap_host, self.imap_username, self.imap_folder):
            if any(c in value for c in "\r\n\0"):
                raise ValueError("Invalid mailbox configuration")
        return self

    def require_configured(self):
        url = urlsplit(self.api_base_url)
        if (
            not self.imap_host
            or not self.imap_username
            or not self.imap_folder
            or not self.process_id
            or not self.imap_password_file
            or not self.api_token_file
            or url.scheme not in ("http", "https")
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("Complete the mailbox, process, API and secret-file configuration")
        for path in (self.imap_password_file, self.api_token_file):
            if not path.is_file() or not path.read_text().strip():
                raise ValueError("A required secret file is missing or empty")
