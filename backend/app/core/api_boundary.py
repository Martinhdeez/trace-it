"""Keep API-configured execution resources inside the operator's deployment boundary."""

from pathlib import Path

from app.core.config import settings


def endpoint(value: str | None, configured: str | None) -> None:
    if not settings.api_token.get_secret_value() or value is None:
        return
    if not configured or value.rstrip("/") != configured.rstrip("/"):
        raise ValueError("Model endpoints must match the deployment configuration")


def model_directory(value: str, root: Path) -> None:
    if settings.api_token.get_secret_value() and not Path(value).resolve().is_relative_to(
        root.resolve()
    ):
        raise ValueError("OCR model directories must stay inside the deployment model directory")


def database_values(value) -> None:
    """Apply the same boundary to raw JSON snapshots as to typed business requests."""
    from app.features.ingestion.config import Settings

    config = Settings()

    def visit(item):
        if isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, dict):
            for name, child in item.items():
                if name in {"local_endpoint", "compatible_endpoint"}:
                    if child is not None and not isinstance(child, str):
                        raise ValueError("Model endpoints must be strings")
                    endpoint(
                        child,
                        settings.local_base_url if name == "local_endpoint" else config.vlm_url,
                    )
                elif name in {"primary_model_dir", "verification_model_dir"}:
                    if not isinstance(child, str):
                        raise ValueError("Model directories must be strings")
                    model_directory(child, config.model_dir)
                visit(child)

    visit(value)
