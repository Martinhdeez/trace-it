"""Explicit, versioned execution choices. Presets only produce editable values."""

from copy import deepcopy
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import settings
from app.features.ingestion.config import Settings as IngestionSettings
from app.features.use_cases.schemas import ROLES, AgentSettings, Role

Preset = Literal["lowest_cost", "fastest", "balanced", "highest_quality"]
PRESETS: tuple[Preset, ...] = ("lowest_cost", "fastest", "balanced", "highest_quality")


class ExtractionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_model_dir: str = Field(min_length=1)
    verification_model_dir: str = Field(min_length=1)
    mode: Literal["local", "api", "hybrid"] = "hybrid"
    ocr: bool = True
    secondary_ocr: bool = True
    # None disables a reader. Explicit prefixes prevent implicit provider selection.
    vision_model: str | None = None  # local:, compatible:, gemini:, helmcode:
    text_judge_model: str | None = None  # local:, compatible:, jev:, helmcode:
    focused_verification: bool = True
    source_verification: bool = True
    dpi: int = Field(default=240, ge=72, le=600)
    vision_timeout_seconds: float = Field(default=60, gt=0, le=600)
    judge_timeout_seconds: float = Field(default=60, gt=0, le=600)
    vision_max_tokens: int = Field(default=4096, ge=128, le=32768)
    judge_max_tokens: int = Field(default=4096, ge=128, le=32768)

    @model_validator(mode="after")
    def readers(self) -> Self:
        for model, providers in (
            (self.vision_model, {"local", "compatible", "gemini", "helmcode"}),
            (self.text_judge_model, {"local", "compatible", "jev", "helmcode"}),
        ):
            if model is not None:
                provider, _, name = model.partition(":")
                if provider not in providers or not name.strip():
                    raise ValueError(f"Reader model must use one of {sorted(providers)} prefixes")
        if (
            self.vision_model
            and self.vision_model.startswith("helmcode:")
            and self.vision_model.split(":", 1)[1] not in {"qwen3.6", "gemma4"}
        ):
            raise ValueError("Helmcode vision supports qwen3.6 and gemma4")
        return self


class ExecutionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset: Preset | Literal["custom"] = "custom"
    local_only: bool = False
    # Pinned non-secret endpoint; credentials are looked up only at execution time.
    local_endpoint: str = Field(min_length=1)
    compatible_endpoint: str | None = None
    agents: dict[Role, AgentSettings]
    extraction: ExtractionSettings

    @model_validator(mode="after")
    def complete(self) -> Self:
        for endpoint in (self.local_endpoint, self.compatible_endpoint):
            if endpoint is None:
                continue
            url = urlsplit(endpoint)
            if url.scheme not in {"http", "https"} or not url.hostname:
                raise ValueError("Model endpoints must be HTTP or HTTPS URLs")
            if url.username or url.password or url.query or url.fragment:
                raise ValueError("Model endpoints cannot contain credentials, queries or fragments")
        if set(self.agents) != set(ROLES):
            raise ValueError("Configure every agent role")
        for role, config in self.agents.items():
            if not config.model or not config.model.strip():
                raise ValueError(f"{role} needs an explicit model")
            for model in [config.model, *config.fallback_models]:
                if not model.strip() or (":" in model and not model.split(":", 1)[1].strip()):
                    raise ValueError(f"{role}: model identifiers cannot be empty")
                if self.local_only and not model.startswith("local:"):
                    raise ValueError(
                        f"{role}: local-only processes require local models and fallbacks"
                    )
        for model in (self.extraction.vision_model, self.extraction.text_judge_model):
            if self.local_only and model and not model.startswith("local:"):
                raise ValueError("Local-only extraction requires local readers")
            if model and model.startswith("compatible:") and not self.compatible_endpoint:
                raise ValueError("A compatible reader needs a compatible endpoint")
        return self


def extraction_defaults() -> ExtractionSettings:
    config = IngestionSettings()
    chain = config.visual_chain()
    vision = f"{chain[0][0]}:{chain[0][1]}" if chain else None
    judge = next(
        (
            f"{provider}:{config.jev_model if provider == 'jev' else config.helmcode_text_model}"
            for provider in config.text_providers
            if (provider == "jev" and config.jev_api_key)
            or (provider == "helmcode" and config.helmcode_api_key)
        ),
        None,
    )
    return ExtractionSettings(
        primary_model_dir=str(config.model_dir),
        verification_model_dir=str(config.model_dir / "verify"),
        vision_model=vision,
        text_judge_model=judge,
        mode=config.ocr_mode,
        dpi=config.ocr_dpi,
        vision_timeout_seconds=config.vlm_timeout,
        judge_timeout_seconds=config.vlm_timeout,
    )


def read(snapshot: dict) -> ExecutionSettings:
    metadata = snapshot.get("execution") or {
        "local_endpoint": settings.local_base_url,
        "compatible_endpoint": IngestionSettings().vlm_url,
        "extraction": extraction_defaults().model_dump(mode="json"),
    }
    return ExecutionSettings.model_validate(
        {
            **metadata,
            "agents": {
                role: {
                    **row["settings"],
                    "model": row["settings"].get("model") or getattr(settings, f"{role}_model"),
                }
                for role, row in snapshot["agents"].items()
            },
        }
    )


def write(snapshot: dict, config: ExecutionSettings) -> None:
    snapshot["execution"] = config.model_dump(mode="json", exclude={"agents"})
    snapshot["agents"] = {
        role: {
            "config_id": snapshot.get("agents", {}).get(role, {}).get("config_id"),
            "settings": agent.model_dump(mode="json"),
        }
        for role, agent in config.agents.items()
    }


def preset(base: ExecutionSettings, name: Preset) -> ExecutionSettings:
    """Start from the supplied models; deployment mappings may replace them per role.

    The labels describe intent, not benchmark claims. Evidence acceptance never changes.
    """
    value = base.model_dump(mode="json")
    timeout, retries, attempts = {
        "lowest_cost": (60, 0, 1),
        "fastest": (15, 0, 1),
        "balanced": (60, 2, 3),
        "highest_quality": (120, 4, 5),
    }[name]
    for role, agent in value["agents"].items():
        agent.update(timeout_seconds=timeout, retries=retries, request_limit=1 + retries)
        if role == "compiler":
            agent["limits"]["max_attempts"] = attempts
        if role == "tester":
            agent["limits"]["max_reviews"] = retries
    value["extraction"].update(
        secondary_ocr=True,
        focused_verification=name in {"balanced", "highest_quality"},
        source_verification=name in {"balanced", "highest_quality"},
        dpi=300 if name == "highest_quality" else 240,
        vision_timeout_seconds=timeout,
        judge_timeout_seconds=timeout,
    )
    if name in {"lowest_cost", "fastest"}:
        value["extraction"].update(mode="local", vision_model=None, text_judge_model=None)
    overrides = deepcopy(settings.execution_presets.get(name, {}))
    for role, patch in overrides.pop("agents", {}).items():
        value["agents"][role].update(patch)
    value["extraction"].update(overrides.pop("extraction", {}))
    value.update(overrides, preset=name)
    return ExecutionSettings.model_validate(value)


def ingestion_settings(config: ExecutionSettings, base: IngestionSettings) -> IngestionSettings:
    """Bind non-secret version settings to this deployment's credentials and resources."""
    import os
    from dataclasses import replace

    extraction = config.extraction
    vision = extraction.vision_model
    provider, _, model = (vision or "disabled:").partition(":")
    judge_provider, _, judge_model = (extraction.text_judge_model or "disabled:").partition(":")
    return replace(
        base,
        model_dir=Path(extraction.primary_model_dir),
        verification_model_dir=Path(extraction.verification_model_dir),
        ocr_dpi=extraction.dpi,
        ocr_mode=extraction.mode,
        # A version selects its readers explicitly; never inherit deployment fallbacks.
        helmcode_api_key=base.helmcode_api_key
        if "helmcode" in {provider, judge_provider}
        else None,
        helmcode_vision_models=(model,) if provider == "helmcode" else (),
        helmcode_text_model=judge_model
        if judge_provider == "helmcode"
        else base.helmcode_text_model,
        vision_providers=("compatible",)
        if provider in {"local", "compatible"}
        else (provider,)
        if provider in {"gemini", "helmcode"}
        else (),
        text_providers=(judge_provider,) if judge_provider in {"jev", "helmcode"} else (),
        vlm_url=config.local_endpoint
        if provider == "local"
        else config.compatible_endpoint
        if provider == "compatible"
        else None,
        vlm_model=model if provider in {"local", "compatible"} else None,
        vlm_api_key=os.getenv("LOCAL_LLM_API_KEY") if provider == "local" else base.vlm_api_key,
        gemini_model=model if provider == "gemini" else base.gemini_model,
        gemini_api_key=base.gemini_api_key if provider == "gemini" else None,
        vlm_timeout=extraction.vision_timeout_seconds,
        vision_max_tokens=extraction.vision_max_tokens,
        jev_model=judge_model,
        jev_api_key=base.jev_api_key if judge_provider == "jev" else None,
        judge_url=config.local_endpoint
        if judge_provider == "local"
        else config.compatible_endpoint
        if judge_provider == "compatible"
        else None,
        judge_api_key=os.getenv("LOCAL_LLM_API_KEY")
        if judge_provider == "local"
        else base.vlm_api_key,
        judge_timeout=extraction.judge_timeout_seconds,
        judge_max_tokens=extraction.judge_max_tokens,
    )
